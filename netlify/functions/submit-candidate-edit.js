// POST /.netlify/functions/submit-candidate-edit
// Stores the candidate's edit as a pending-review row in the private submissions
// sheet. Every submission carries the submitter's own name/email/declaration
// (collected in the submit modal); Gina verifies and approves each one by hand.
// The on-file campaign email (if any) is stored alongside as a cross-check.
// No verification email is sent (the magic-link flow in verify-candidate-edit.js
// is dormant — flip it back on if volume ever outgrows manual review).
// Nothing here ever writes to the public sheet; publishing stays manual.
const crypto = require('crypto');
const { readRange, appendRow, sendEmail, candidateSlug } = require('./lib');

const STANCES = ['Agree', 'Disagree', 'No opinion'];
// Server-side mirror of the editor's submission gates (client checks are advisory only).
const PROFANITY_RE = /\b\w*(fuck|shit|bitch|nigger|faggot)\w*\b|\b(cunt\w*|asshole\w*|goddamn\w*|whore\w*|slut\w*)\b/i;
const LIMITS = { hook1: 140, hook2: 320 };
const OWNWORDS_MAX = 400;

const json = (statusCode, body) => ({ statusCode, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });

  let p;
  try { p = JSON.parse(event.body); } catch { return json(400, { error: 'Bad JSON' }); }

  // Validate — server-side mirror of the editor's constraints.
  if (!p.candidate || !p.slug) return json(400, { error: 'Missing candidate' });
  if (!p.consent) return json(400, { error: 'Consent is required' });
  if (!(p.submitterName || '').trim() || !(p.submitterRole || '').trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(p.submitterEmail || '')) {
    return json(400, { error: 'Submitter name, role, and email are required' });
  }
  if ((p.hook1 || '').length > LIMITS.hook1 || (p.hook2 || '').length > LIMITS.hook2) return json(400, { error: 'Hook too long' });
  for (const v of Object.values(p.positions || {})) {
    if (!STANCES.includes(v)) return json(400, { error: 'Bad stance value' });
  }
  for (const perIssue of Object.values(p.statementReactions || {})) {
    for (const v of Object.values(perIssue || {})) {
      if (!['up', 'down', 'skip'].includes(v)) return json(400, { error: 'Bad reaction value' });
    }
  }
  for (const v of Object.values(p.ownWords || {})) {
    if ((v || '').length > OWNWORDS_MAX) return json(400, { error: 'Own-words too long' });
  }
  if ((p.photoDataUrl || '').length > 48000) return json(400, { error: 'Photo too large' });
  const hasContent = Object.values(p.statementReactions || {}).some((r) => Object.keys(r || {}).length > 0)
    || Object.values(p.ownWords || {}).some((v) => (v || '').trim())
    || Object.values(p.notes || {}).some((v) => (v || '').trim())
    || p.photoChanged || (p.hook1 || '').trim() || (p.hook2 || '').trim() || (p.website || '').trim();
  if (!hasContent) return json(400, { error: 'Empty submission' });
  const texts = [p.hook1, p.hook2, ...Object.values(p.ownWords || {}), ...Object.values(p.notes || {})];
  if (texts.some((t) => t && PROFANITY_RE.test(t))) return json(400, { error: 'Please remove the strong language before submitting' });

  // On-file campaign email (from the private contacts tab) — stored with the row
  // so Gina can cross-check it against the submitter's address during review.
  const contacts = await readRange('contacts!A2:D');
  const match = contacts.find((row) => candidateSlug(row[0]) === p.slug);
  const onFileEmail = match && (match[3] || '').includes('@') ? match[3].trim() : '';

  const id = crypto.randomUUID();
  await appendRow('submissions', [
    id, 'pending-review', new Date().toISOString(), '',
    p.candidate, p.slug, p.office || '', p.party || '',
    onFileEmail, p.website || '', p.hook1 || '', p.hook2 || '',
    JSON.stringify(p.positions || {}), JSON.stringify(p.ownWords || {}), JSON.stringify(p.notes || {}),
    p.photoChanged ? 'yes' : 'no', p.photoDataUrl || '', 'yes', JSON.stringify(p.statementReactions || {}),
    p.submitterName.trim(), p.submitterRole.trim(), p.submitterEmail.trim(),
    p.whatChanged || '',
  ]);

  // Heads-up to Gina when email sending is configured; silently skipped otherwise.
  if (process.env.NOTIFY_EMAIL) {
    await sendEmail(
      process.env.NOTIFY_EMAIL,
      `VYV: profile submission for ${p.candidate}`,
      `<p><b>${p.submitterName.trim()}</b> (${p.submitterRole.trim()}, ${p.submitterEmail.trim()}) submitted profile updates for <b>${p.candidate}</b>${onFileEmail ? ` — on-file email: ${onFileEmail}` : ' — no email on file'}. Review the submissions tab in the private sheet.</p>`,
    );
  }

  return json(200, { ok: true, verify: 'manual' });
};
