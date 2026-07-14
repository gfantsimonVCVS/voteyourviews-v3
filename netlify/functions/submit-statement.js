// Statement-review submissions → the "Statement Submissions" matrix tab of the
// public master sheet: statements live in fixed rows (4–30), and each reviewer
// owns a column pair (Suggested Edit | Notes) keyed by their email, so Gina reads
// submissions side-by-side like the bake-off sheet. Re-submitting overwrites the
// reviewer's own cells — the matrix is the single record of submissions.
const { readRange, updateRange, sheetsFetch } = require('./lib');

const MASTER_SHEET_ID = '1V1oaEy6ToV3LZt0et9bIWEJQbPrYZg73tDxGelhiFn8';
const MATRIX_TAB = 'Statement Submissions';
const FIRST_BLOCK_COL = 4; // column D (1-indexed) — first reviewer block after issue/text/order

// 1-indexed column number → A1 letter(s)
function colLetter(n) {
  let s = '';
  while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

const json = (statusCode, body) => ({
  statusCode,
  headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
  body: JSON.stringify(body),
});

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type' } };
  }
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });

  let p;
  try { p = JSON.parse(event.body || '{}'); } catch { return json(400, { error: 'bad JSON' }); }
  const issue = (p.issue || '').trim();
  const stmtNum = String(p.stmtNum || '').trim();       // 1-based within the issue
  const suggestion = (p.suggestion || '').trim();
  const reason = (p.reason || '').trim();
  const name = (p.name || '').trim();
  const email = (p.email || '').trim().toLowerCase();
  const submitted = (p.submitted || '').trim();
  if (!issue || !stmtNum || !name || !email || (!suggestion && !reason)) {
    return json(400, { error: 'missing fields' });
  }

  // Locate the statement's row: col A is "Issue N" (display label); hidden col C
  // holds the order as a fallback for older label formats.
  const grid = await readRange(`${MATRIX_TAB}!A4:C40`, MASTER_SHEET_ID);
  const rowOffset = grid.findIndex((r) => {
    const label = (r[0] || '').trim();
    return label === `${issue} ${stmtNum}` || (label === issue && String(r[2] || '').trim() === stmtNum);
  });
  if (rowOffset === -1) return json(404, { error: 'statement not found' });
  const row = 4 + rowOffset;

  // Locate (or create) this reviewer's column pair — row 2 holds "Name <email>" per block.
  const idRow = (await readRange(`${MATRIX_TAB}!2:2`, MASTER_SHEET_ID))[0] || [];
  let col = null;
  for (let c = FIRST_BLOCK_COL; c < idRow.length + 2; c += 2) {
    const cell = (idRow[c - 1] || '').toLowerCase();
    if (cell.includes(email)) { col = c; break; }
    if (!cell) { break; }
  }
  if (col === null) {
    // first empty even-offset block after existing ones
    col = FIRST_BLOCK_COL;
    while ((idRow[col - 1] || '').trim() !== '') col += 2;
  }
  const cL = colLetter(col), cR = colLetter(col + 1);

  // Grow the grid if this block would run past it — a values write beyond the
  // sheet's column count hard-fails ("exceeds grid limits") instead of expanding.
  const meta = await sheetsFetch(`?fields=sheets(properties(sheetId,title,gridProperties(columnCount)))`, {}, MASTER_SHEET_ID);
  const tab = (meta.sheets || []).find((s) => s.properties.title === MATRIX_TAB);
  if (tab && tab.properties.gridProperties.columnCount < col + 1) {
    await sheetsFetch(`:batchUpdate`, {
      method: 'POST',
      body: JSON.stringify({ requests: [{ appendDimension: { sheetId: tab.properties.sheetId, dimension: 'COLUMNS', length: (col + 1) - tab.properties.gridProperties.columnCount + 20 } }] }),
    }, MASTER_SHEET_ID);
  }

  // Block headers (idempotent) + the statement's cells.
  await updateRange(`${MATRIX_TAB}!${cL}1:${cR}3`, [
    [name, 'Notes'],
    [email, ''],
    [submitted, ''],
  ], MASTER_SHEET_ID);
  await updateRange(`${MATRIX_TAB}!${cL}${row}:${cR}${row}`, [[suggestion, reason]], MASTER_SHEET_ID);

  return json(200, { ok: true });
};
