// Per-candidate OG tags for clean candidate URLs (voteyourviews.org/GinaHinojosa).
// Social scrapers don't run JavaScript, so the SPA's static meta tags are all they see.
// This function intercepts /<slug> requests, looks the slug up in icons/og/manifest.json
// (written by tools/generate-og-cards.py), and rewrites the OG/Twitter tags in index.html
// to that candidate's name, office, and share card before the HTML leaves Netlify.

let manifestCache = null;
let manifestFetchedAt = 0;
const MANIFEST_TTL_MS = 5 * 60 * 1000;

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export default async (request, context) => {
  const url = new URL(request.url);
  // Only bare candidate paths (or their /edit page). Anything with a dot, or a known
  // app path, falls straight through to normal serving.
  const m = url.pathname.match(/^\/([A-Za-z0-9]+)(\/edit\/?)?$/);
  if (!m) return context.next();
  const slug = m[1].toLowerCase();

  const now = Date.now();
  if (!manifestCache || now - manifestFetchedAt > MANIFEST_TTL_MS) {
    try {
      const res = await fetch(new URL('/icons/og/manifest.json', url.origin));
      if (res.ok) {
        manifestCache = await res.json();
        manifestFetchedAt = now;
      }
    } catch (_) { /* serve untouched below */ }
  }
  const cand = manifestCache && manifestCache[slug];
  if (!cand) return context.next();

  const response = await context.next();
  const html = await response.text();

  const title = `${cand.name} — ${cand.office} | VoteYourViews.org`;
  const description = `See where ${cand.name} stands on the issues — and find out in 2 minutes if your views match.`;
  const image = `${url.origin}/icons/og/${slug}.png`;
  const pageUrl = `${url.origin}/${m[1]}`;

  const rewritten = html
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`)
    .replace(/<meta name="description" content="[^"]*">/, `<meta name="description" content="${esc(description)}">`)
    .replace(/<meta property="og:title" content="[^"]*">/, `<meta property="og:title" content="${esc(title)}">`)
    .replace(/<meta property="og:description" content="[^"]*">/, `<meta property="og:description" content="${esc(description)}">`)
    .replace(/<meta property="og:image" content="[^"]*">/, `<meta property="og:image" content="${image}">\n  <meta property="og:url" content="${pageUrl}">`)
    .replace(/<meta name="twitter:title" content="[^"]*">/, `<meta name="twitter:title" content="${esc(title)}">`)
    .replace(/<meta name="twitter:description" content="[^"]*">/, `<meta name="twitter:description" content="${esc(description)}">`)
    .replace(/<meta name="twitter:image" content="[^"]*">/, `<meta name="twitter:image" content="${image}">`);

  const headers = new Headers(response.headers);
  headers.delete('content-length'); // body length changed
  return new Response(rewritten, { status: response.status, headers });
};

export const config = {
  path: '/*',
  excludedPath: ['/icons/*', '/images/*', '/tools/*', '/Docs/*', '/*.html', '/*.js', '/*.css', '/*.png', '/*.jpg', '/*.json', '/*.gs'],
};
