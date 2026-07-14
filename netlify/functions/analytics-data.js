// GA4 Data API proxy for the /analytics dashboard. The service account queries
// the VoteYourViews property server-side (credentials never reach the browser);
// the browser may only request the named reports below — no free-form queries.
const crypto = require('crypto');

const PROPERTY = 'properties/545465518';
const b64url = (buf) => Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

let cachedToken = null;
async function gaToken() {
  if (cachedToken && cachedToken.exp > Date.now() + 60000) return cachedToken.token;
  const sa = JSON.parse(process.env.GOOGLE_SA_JSON);
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claims = b64url(JSON.stringify({
    iss: sa.client_email,
    scope: 'https://www.googleapis.com/auth/analytics.readonly',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now, exp: now + 3600,
  }));
  const sig = crypto.createSign('RSA-SHA256').update(`${header}.${claims}`).sign(sa.private_key);
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${header}.${claims}.${b64url(sig)}`,
  });
  if (!res.ok) throw new Error(`GA token exchange failed: ${res.status}`);
  const data = await res.json();
  cachedToken = { token: data.access_token, exp: Date.now() + data.expires_in * 1000 };
  return cachedToken.token;
}

const dim = (name) => ({ name });
const met = (name) => ({ name });
const evFilter = (event) => ({ filter: { fieldName: 'eventName', stringFilter: { value: event } } });

// Named reports — range placeholders {start}/{end} are filled per-request.
const REPORTS = {
  // Daily users + events over time
  traffic: {
    dimensions: [dim('date')],
    metrics: [met('activeUsers'), met('eventCount'), met('sessions')],
    orderBys: [{ dimension: { dimensionName: 'date' } }],
  },
  // How users respond to each statement (issue × statement # × agree/disagree/skip)
  statements: {
    dimensions: [dim('customEvent:issue'), dim('customEvent:statement'), dim('customEvent:response')],
    metrics: [met('eventCount')],
    dimensionFilter: evFilter('statement_response'),
    limit: '250',
  },
  // Candidate popularity: profile views by candidate
  candidates: {
    dimensions: [dim('customEvent:candidate'), dim('customEvent:party')],
    metrics: [met('eventCount')],
    dimensionFilter: evFilter('candidate_profile_view'),
    orderBys: [{ metric: { metricName: 'eventCount' }, desc: true }],
    limit: '25',
  },
  // Ballot picks by candidate
  ballotPicks: {
    dimensions: [dim('customEvent:candidate')],
    metrics: [met('eventCount')],
    dimensionFilter: evFilter('add_to_ballot'),
    orderBys: [{ metric: { metricName: 'eventCount' }, desc: true }],
    limit: '25',
  },
  // Journey: users reaching each screen (funnel material)
  screens: {
    dimensions: [dim('customEvent:screen')],
    metrics: [met('activeUsers'), met('eventCount')],
    dimensionFilter: evFilter('screen_change'),
    orderBys: [{ metric: { metricName: 'activeUsers' }, desc: true }],
    limit: '25',
  },
  // Key milestones (quiz completes, prints, lookups, submissions)
  milestones: {
    dimensions: [dim('eventName')],
    metrics: [met('eventCount'), met('activeUsers')],
    dimensionFilter: { filter: { fieldName: 'eventName', inListFilter: { values: [
      'quiz_complete', 'ballot_print', 'address_lookup', 'statement_edit_submitted', 'issue_answered', 'candidate_profile_view', 'add_to_ballot',
    ] } } },
    limit: '25',
  },
  // Counties looked up
  counties: {
    dimensions: [dim('customEvent:county')],
    metrics: [met('eventCount')],
    dimensionFilter: evFilter('address_lookup'),
    orderBys: [{ metric: { metricName: 'eventCount' }, desc: true }],
    limit: '30',
  },
};

const json = (statusCode, body) => ({
  statusCode,
  headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'public, max-age=300' },
  body: JSON.stringify(body),
});

exports.handler = async (event) => {
  const q = event.queryStringParameters || {};
  const spec = REPORTS[q.report];
  if (!spec) return json(400, { error: 'unknown report', reports: Object.keys(REPORTS) });
  const days = Math.min(Math.max(parseInt(q.days || '28', 10) || 28, 1), 400);

  const body = { ...spec, dateRanges: [{ startDate: `${days}daysAgo`, endDate: 'today' }] };
  try {
    const token = await gaToken();
    const res = await fetch(`https://analyticsdata.googleapis.com/v1beta/${PROPERTY}:runReport`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) return json(502, { error: `GA API ${res.status}`, detail: (await res.text()).slice(0, 300) });
    const data = await res.json();
    const rows = (data.rows || []).map((r) => ({
      d: (r.dimensionValues || []).map((v) => v.value),
      m: (r.metricValues || []).map((v) => Number(v.value)),
    }));
    return json(200, { rows, rowCount: data.rowCount || 0 });
  } catch (e) {
    return json(500, { error: e.message });
  }
};
