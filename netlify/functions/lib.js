// Shared helpers for the candidate-edit functions: Google Sheets access via the
// service account (no npm deps — JWT signed with node:crypto), magic-link token
// signing, and Resend email. Config comes from Netlify env vars:
//   GOOGLE_SA_JSON     — full service-account key JSON (one line)
//   PRIVATE_SHEET_ID   — the private contacts+submissions spreadsheet
//   EDIT_LINK_SECRET   — HMAC secret for magic-link tokens
//   RESEND_API_KEY     — optional; without it no email is sent and submissions
//                        fall back to manual verification
//   NOTIFY_EMAIL       — where "new verified submission" alerts go
const crypto = require('crypto');

const b64url = (buf) => Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

// --- Google Sheets REST (service account JWT → access token) ---
let cachedToken = null; // { token, exp } — warm-lambda reuse
async function googleToken() {
  if (cachedToken && cachedToken.exp > Date.now() + 60000) return cachedToken.token;
  const sa = JSON.parse(process.env.GOOGLE_SA_JSON);
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claims = b64url(JSON.stringify({
    iss: sa.client_email,
    scope: 'https://www.googleapis.com/auth/spreadsheets',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now, exp: now + 3600,
  }));
  const sig = crypto.createSign('RSA-SHA256').update(`${header}.${claims}`).sign(sa.private_key);
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${header}.${claims}.${b64url(sig)}`,
  });
  if (!res.ok) throw new Error(`Google token exchange failed: ${res.status}`);
  const data = await res.json();
  cachedToken = { token: data.access_token, exp: Date.now() + data.expires_in * 1000 };
  return cachedToken.token;
}

// sheetId defaults to the private contacts sheet; pass one explicitly to hit the
// public master sheet (e.g. the Statement Submissions matrix).
async function sheetsFetch(path, options = {}, sheetId = process.env.PRIVATE_SHEET_ID) {
  const token = await googleToken();
  const res = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId}${path}`,
    { ...options, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers } },
  );
  if (!res.ok) throw new Error(`Sheets API ${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

const readRange = (range, sheetId) => sheetsFetch(`/values/${encodeURIComponent(range)}`, {}, sheetId).then((d) => d.values || []);

const appendRow = (tab, row, sheetId) => sheetsFetch(`/values/${encodeURIComponent(tab)}:append?valueInputOption=RAW`, {
  method: 'POST', body: JSON.stringify({ values: [row] }),
}, sheetId);

const updateRange = (range, values, sheetId) => sheetsFetch(`/values/${encodeURIComponent(range)}?valueInputOption=RAW`, {
  method: 'PUT', body: JSON.stringify({ values }),
}, sheetId);

// --- magic-link tokens: HMAC over "id.exp" ---
const signToken = (id, exp) => b64url(crypto.createHmac('sha256', process.env.EDIT_LINK_SECRET).update(`${id}.${exp}`).digest());

function verifyToken(id, exp, sig) {
  if (!id || !exp || !sig || Number(exp) < Date.now()) return false;
  const expected = signToken(id, exp);
  return expected.length === sig.length && crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(sig));
}

// --- email via Resend; returns false (never throws) when unconfigured/failing,
// so the submission still lands in the queue for manual verification ---
async function sendEmail(to, subject, html) {
  if (!process.env.RESEND_API_KEY) return false;
  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${process.env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: 'VoteYourViews <verify@voteyourviews.org>', to: [to], subject, html }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// Same slug rule as the app (index.html candidateSlug) and the OG edge function.
const candidateSlug = (name) => (name || '').toLowerCase().replace(/[^a-z0-9]/g, '');

module.exports = { readRange, appendRow, updateRange, sheetsFetch, signToken, verifyToken, sendEmail, candidateSlug };
