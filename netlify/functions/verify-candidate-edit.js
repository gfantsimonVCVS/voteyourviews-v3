// GET /.netlify/functions/verify-candidate-edit?id=…&exp=…&sig=…
// Magic-link target. Validates the signed token, marks the submission row
// verified (one-time — an already-verified id shows "already confirmed"),
// and emails Gina that a verified submission is waiting for approval.
const { readRange, updateRange, verifyToken, sendEmail } = require('./lib');

const page = (title, body) => ({
  statusCode: 200,
  headers: { 'Content-Type': 'text/html; charset=utf-8' },
  body: `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title} — VoteYourViews</title></head>
<body style="margin:0;font-family:-apple-system,Segoe UI,sans-serif;background:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh">
<div style="max-width:420px;text-align:center;padding:40px 24px">
  <div style="font-size:44px;margin-bottom:12px">${title === 'Confirmed' ? '✅' : 'ℹ️'}</div>
  <h1 style="font-size:22px;color:#0f172a;margin:0 0 10px">${title === 'Confirmed' ? 'Thanks — your updates are confirmed.' : title}</h1>
  <p style="color:#475569;line-height:1.5;margin:0 0 24px">${body}</p>
  <a href="/" style="display:inline-block;padding:12px 22px;background:#0f172a;color:#fff;border-radius:10px;text-decoration:none;font-weight:bold">Go to VoteYourViews</a>
</div></body></html>`,
});

exports.handler = async (event) => {
  const { id, exp, sig } = event.queryStringParameters || {};
  if (!verifyToken(id, exp, sig)) {
    return page('Link expired or invalid', 'This confirmation link is no longer valid. You can re-submit your updates from your profile’s edit page to get a fresh link.');
  }

  const rows = await readRange('submissions!A2:E');
  const idx = rows.findIndex((r) => r[0] === id);
  if (idx === -1) return page('Link expired or invalid', 'We couldn’t find this submission. Please re-submit from your profile’s edit page.');

  const [, status, , , candidate] = rows[idx];
  if (status !== 'pending-verify') {
    return page('Already confirmed', 'These updates were already confirmed. The VoteYourViews team reviews every submission before it goes live.');
  }

  const rowNum = idx + 2;
  await updateRange(`submissions!B${rowNum}:D${rowNum}`, [['verified', rows[idx][2] || '', new Date().toISOString()]]);

  if (process.env.NOTIFY_EMAIL) {
    await sendEmail(
      process.env.NOTIFY_EMAIL,
      `VYV: verified profile submission from ${candidate}`,
      `<p><b>${candidate}</b> confirmed their profile updates. Review row ${rowNum} of the submissions tab in the private sheet, then apply what you approve to the public sheet.</p>`,
    );
  }

  return page('Confirmed', 'The VoteYourViews team will review your updates and publish them to your public profile. You’ll see them live once approved.');
};
