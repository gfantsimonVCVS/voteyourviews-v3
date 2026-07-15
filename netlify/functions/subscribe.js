// Mailing-list signup → appends to the PRIVATE contacts sheet (never the public
// master sheet — subscriber emails are PII and the master sheet is published to
// the web). Replaces the dead Google Apps Script endpoint whose no-cors POSTs
// failed silently. Same-origin, so the app gets a real success/failure response.
const { appendRow } = require('./lib');

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method not allowed' };
  let data;
  try { data = JSON.parse(event.body || '{}'); } catch { return { statusCode: 400, body: JSON.stringify({ ok: false, error: 'bad json' }) }; }

  const email = String(data.email || '').trim().slice(0, 254);
  if (!EMAIL_RE.test(email)) return { statusCode: 400, body: JSON.stringify({ ok: false, error: 'invalid email' }) };
  if (data.website) return { statusCode: 200, body: JSON.stringify({ ok: true }) }; // honeypot field — pretend success to bots

  const clip = (v, n) => String(v || '').slice(0, n);
  try {
    await appendRow('MailingList', [
      new Date().toISOString(),
      email,
      clip(data.county, 80),
      clip(data.address, 200),
      clip(data.source, 60),
    ]);
    return { statusCode: 200, body: JSON.stringify({ ok: true }) };
  } catch (e) {
    console.error('subscribe append failed:', e.message);
    return { statusCode: 502, body: JSON.stringify({ ok: false, error: 'store failed' }) };
  }
};
