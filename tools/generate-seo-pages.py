#!/usr/bin/env python3
# RE-RUN THIS after any roster / position / photo change in the Google Sheet, BEFORE deploy:
#     python3 tools/generate-seo-pages.py
# It rewrites candidates/, races/ and sitemap.xml from scratch (stale pages are removed).
"""Generate static, crawlable HTML pages for every candidate and every race.

Netlify serves real files before the `/*  /index.html  200` SPA fallback, so pages written to
candidates/<slug>/index.html and races/<race-slug>/index.html are handed to Google as real HTML
on first byte. The clean app URLs (/JamesTalarico) are untouched — the candidate-og edge function
early-returns on anything that isn't a bare /<slug>, so the two-segment paths below never collide
with it. Each static page links INTO the app at its clean URL.

Data source: the same Google Sheet the app reads (gviz CSV export), same tabs and the same
canonical slug rule as tools/generate-og-cards.py. Nothing is ever invented: a blank sheet field
simply omits its section.

Nonpartisan by construction: every candidate gets identical treatment (same card, same photo size,
same neutral gray party chip), candidates are ordered alphabetically inside a race, and the
Agree/Disagree/Unknown chips use neutral grays — never green-good / red-bad.
"""
import csv, datetime, html, io, json, os, re, shutil, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET_ID = '1V1oaEy6ToV3LZt0et9bIWEJQbPrYZg73tDxGelhiFn8'
# Shared tabs first (three-tab architecture) so their canonical rows win the per-slug dedupe.
TABS = ['Statewide', 'Districts', 'HaysCounty', 'TravisCounty']
COUNTY_DIR = {'Statewide': 'statewide', 'Districts': 'statewide',
              'HaysCounty': 'hays', 'TravisCounty': 'travis'}
SITE = 'https://www.voteyourviews.org'   # www is canonical; the apex redirects here
SITE_NAME = 'VoteYourViews'
DEFAULT_OG = f'{SITE}/icons/og-main.png'
TODAY = datetime.date.today().isoformat()

# owner may set False to hide hook2 on static pages until the neutrality pass
SHOW_HOOK2 = True

ELECTION_LINE = 'Texas Midterm 2026 — Election Day November 3, 2026 · early voting October 19–30'

DATE_TILES = [('Early voting', 'Oct 19–30'), ('Election Day', 'Nov 3'),
              ('Register by', 'Oct 5'), ('Polls open', '7A–7P')]

# Human issue labels + order, mirrored from index.html (GRID_ORDER + ISSUES_RAW topics).
# All nine issues VoteYourViews publishes; icons live at icons/<key>.png.
ISSUES = [
    ('reproductiveRights', 'Reproductive Rights'),
    ('immigration',        'Immigration & Border'),
    ('affordability',      'Housing & Affordability'),
    ('education',          'Public Education'),
    ('electionIntegrity',  'Election Integrity'),
    ('healthcare',         'Healthcare'),
    ('socialSecurity',     'Social Security & Medicare'),
    ('gunPolicy',          'Gun Policy'),
    ('climate',            'Climate & Energy'),
]

# index.html: PARTY_NAME — unknown/blank codes read as Independent.
PARTY_NAME = {'D': 'Democrat', 'R': 'Republican', 'I': 'Independent',
              'L': 'Libertarian', 'G': 'Green'}

# index.html ~line 465: photos live in BOTH the sheet `photo` column and this map.
PHOTO_FALLBACK = {
    'James Talarico': 'https://lh3.googleusercontent.com/d/1xT_tzvyzpedvvRDZJ3V09TqjcoTiPiDO',
    'Maggie Hernandez-Moreno': 'https://lh3.googleusercontent.com/d/1K6T4raB32Hv4zismhpBZAZe0768DNu1L',
    'Beth Smith': 'https://lh3.googleusercontent.com/d/1--CHI_DGGt73n7nD-Zq5GkbMpZIOk0NH',
    'Sandra Bryant': 'https://lh3.googleusercontent.com/d/1ckAyPB35hCDpTT5NFpCZbUfCK4Mmz_y4',
}

CATEGORY_IMG = {'federal': '/icons/Federal.png', 'state': '/icons/State.png',
                'county': '/icons/County.png', 'judicial': '/icons/Judicial.png'}
CATEGORY_ORDER = ['federal', 'state', 'county', 'judicial', 'other']

canonical_slug = lambda name: re.sub(r'[^a-z0-9]', '', (name or '').lower())


def photo_slug(name):
    n = unicodedata.normalize('NFKD', name)
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return re.sub(r'^-|-$', '', re.sub(r'[^a-zA-Z0-9]+', '-', n)).lower()


def pretty_slug(name):
    """PascalCase clean-URL form the app uses: 'James Talarico' -> 'JamesTalarico'."""
    n = unicodedata.normalize('NFKD', name)
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return ''.join(w[:1].upper() + w[1:] for w in re.findall(r'[A-Za-z0-9]+', n))


def race_slug(office):
    # drop the dots inside abbreviations first so "U.S. Senate" -> us-senate (not u-s-senate)
    s = re.sub(r'\b([A-Za-z])\.', r'\1', office)
    s = s.replace('—', ' ').replace('–', ' ').replace('•', ' ').replace('&', ' and ')
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return re.sub(r'-+', '-', s)


def fetch_csv(tab):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab}'
    text = urllib.request.urlopen(url).read().decode('utf-8')
    # same sanitize as the app: drop junk trailing empty columns (otherwise PapaParse-style
    # parsers lose the first data row)
    lines = [re.sub(r'(,"")+\s*$', '', l) for l in text.replace('\r', '').split('\n')]
    return list(csv.DictReader(io.StringIO('\n'.join(lines))))


def load_photo_manifest():
    p = os.path.join(ROOT, 'images', 'candidates', 'manifest.json')
    try:
        return set(json.load(open(p)))
    except Exception:
        return set()


PHOTO_MANIFEST = load_photo_manifest()


def resolve_photo(row, county_dir):
    """Same precedence as the app (resolveLocalPhoto): self-hosted local file, then the sheet
    `photo` cell, then the PHOTO_FALLBACK map. Returns None when there is genuinely no photo —
    the page then omits the image rather than showing a placeholder."""
    party = (row.get('party') or 'NA').strip().upper()
    slug = photo_slug(row['name'])
    for d in (f'{county_dir}/{party}', f'statewide/{party}'):
        if f'{d}/{slug}.png' in PHOTO_MANIFEST:
            return f'/images/candidates/{d}/{slug}.png'
    if county_dir == 'statewide':
        tail = f'/{party}/{slug}.png'
        for rel in sorted(PHOTO_MANIFEST):
            if rel.endswith(tail):
                return f'/images/candidates/{rel}'
    url = (row.get('photo') or '').strip()
    if url.startswith('http'):
        return url
    fb = PHOTO_FALLBACK.get(row['name'].strip())
    return fb or None


E = lambda s: html.escape((s or '').strip(), quote=True)

# The sheet marks key phrases with **double asterisks**. Escape first, then turn the
# markers into <strong>; an unmatched ** is left exactly as typed.
BOLD_RE = re.compile(r'\*\*(.+?)\*\*', re.S)


def hook_html(s):
    """HTML for hook1/hook2/summary text: escaped, with **bold** markers rendered."""
    return BOLD_RE.sub(r'<strong>\1</strong>', E(s))


def clip(text, n=155):
    t = re.sub(r'\s+', ' ', (text or '').strip())
    if len(t) <= n:
        return t
    return t[:n - 1].rsplit(' ', 1)[0] + '…'


def abs_url(u):
    return u if u.startswith('http') else SITE + u


# ────────────────────────────────────────────────────────────────────────── design
# Mirrors the app's own brand: slate-navy chrome (#0f172a), amber action color (#f59e0b),
# Inter for UI/body + Barlow Condensed for the display line — the same two families the app
# already loads, in one Google Fonts request.

CSS = """
:root{
 --navy:#0f172a;--navy-2:#1e293b;--navy-3:#0b1220;--ink:#111827;--muted:#4b5563;
 --line:#e2e8f0;--bg:#f6f7f9;--card:#ffffff;--amber:#f59e0b;--amber-soft:#fde68a;
 --slate:#334155;--focus:#1d4ed8;
 --s1:8px;--s2:16px;--s3:24px;--s4:32px;--s5:48px;
 --z-header:10;
 /* ── type scale (mirrors HaysVotes). One place to resize the whole site.
    Nothing on the page is allowed below --fs-min. ── */
 --fs-min:13px;      /* absolute floor — never prose */
 --fs-small:14px;    /* footer, disclaimer, breadcrumb, pager direction */
 --fs-eyebrow:15px;  /* small-caps kickers, tile labels */
 --fs-label:16px;    /* chips, buttons, nav, section-head chips */
 --fs-hook2:17px;    /* hook2 / "About <First>" story paragraphs */
 --fs-why:17px;      /* office descriptions */
 --fs-body:18px;     /* body copy floor (line-height 1.55) */
 --fs-hook1:20px;    /* hook1 pull-quotes */
 --fs-name:21px;     /* candidate names */
 --fs-h3:22px;       /* h3 */
 --fs-h2:22px;       /* h2 + amber section-head chips */
 --fs-tile:24px;     /* date-strip values */
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:'Inter',system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;
 font-size:var(--fs-body);line-height:1.55;-webkit-font-smoothing:antialiased}
img{max-width:100%}
a{color:#1d4ed8}
a:focus-visible{outline:3px solid var(--focus);outline-offset:2px;border-radius:4px}
.wrap{max-width:960px;margin:0 auto;padding:0 18px}
.disp{font-family:'Barlow Condensed','Inter',system-ui,sans-serif;font-weight:700}

/* ── masthead: logo + chip nav, current page filled amber ── */
header.bar{background:var(--navy);border-bottom:4px solid var(--amber);
 position:relative;z-index:var(--z-header)}
header.bar .wrap{padding:11px 18px}
header.bar img{height:32px;width:auto;display:block}
header.bar a:focus-visible{outline-color:#fff}
nav.top{margin-top:9px;display:flex;flex-wrap:wrap;gap:6px}
nav.top a{display:inline-flex;align-items:center;min-height:40px;padding:4px 12px;
 font-family:'Barlow Condensed','Inter',sans-serif;font-size:var(--fs-label);font-weight:700;
 letter-spacing:.09em;text-transform:uppercase;color:#dbe4f2;text-decoration:none;
 background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.2);border-radius:6px}
nav.top a:hover{background:rgba(245,158,11,.16);color:#fff;border-color:var(--amber)}
nav.top a[aria-current="page"]{background:var(--amber);color:var(--navy);border-color:var(--amber)}

/* ── hero band ── */
.hero{background:linear-gradient(165deg,var(--navy-3) 0%,var(--navy) 100%);color:#fff;
 border-bottom:4px solid var(--amber)}
.hero .wrap{padding-top:var(--s2);padding-bottom:var(--s3)}
.hero .crumb{font-size:var(--fs-small);color:#b9c8dd;margin:0 0 12px}
.hero .crumb a{color:#cfdcee}
.kicker{font-family:'Barlow Condensed','Inter',sans-serif;font-weight:700;font-size:var(--fs-eyebrow);
 letter-spacing:.18em;text-transform:uppercase;color:var(--amber-soft);margin:0 0 var(--s1)}
.hero h1{font-family:'Barlow Condensed','Inter',sans-serif;font-weight:700;
 font-size:clamp(32px,7.4vw,52px);line-height:.98;letter-spacing:-.02em;text-transform:uppercase;
 color:#fff;margin:0;text-wrap:balance;overflow-wrap:break-word}
.hrule{width:52px;height:4px;background:var(--amber);margin:12px 0 0;border-radius:2px}
.role{color:#ccd9ea;font-size:var(--fs-body);margin:12px 0 0;max-width:56ch;overflow-wrap:break-word}
/* subline: office on its own line, party on the next — never wrapping mid-sentence */
.role .role-l{display:block}
.role .party-l{display:block;margin-top:6px;font-family:'Barlow Condensed','Inter',sans-serif;
 font-size:var(--fs-label);font-weight:700;letter-spacing:.12em;text-transform:uppercase;
 color:var(--amber-soft)}
.idrow{display:flex;gap:var(--s2);align-items:center;flex-wrap:wrap}
.idrow>div{flex:1 1 240px;min-width:0}
.avatar{width:92px;height:92px;flex:0 0 auto;border-radius:50%;object-fit:cover;
 object-position:top center;background:#e7ebf0;
 box-shadow:0 0 0 3px var(--navy),0 0 0 6px var(--amber),0 3px 10px rgba(0,0,0,.3)}

/* dates tiles */
.tiles{list-style:none;display:flex;flex-wrap:wrap;padding:0;margin:var(--s3) 0 0;
 background:rgba(255,255,255,.06);border-top:2px solid rgba(245,158,11,.45);max-width:560px}
.tiles li{flex:1 1 40%;min-width:118px;padding:10px 13px;border-right:1px solid rgba(255,255,255,.14)}
.tiles li:last-child{border-right:none}
.tiles b{display:block;font-size:var(--fs-eyebrow);font-weight:800;letter-spacing:.1em;
 text-transform:uppercase;color:var(--amber-soft);line-height:1.2}
.tiles span{display:block;font-family:'Barlow Condensed','Inter',sans-serif;font-size:var(--fs-tile);
 font-weight:700;color:#fff;line-height:1.05;margin-top:2px}

/* ── actions ── */
.cta{display:inline-flex;align-items:center;justify-content:center;min-height:54px;
 padding:0 22px;background:linear-gradient(180deg,#fbbf24,#f59e0b);color:#0f172a!important;
 text-decoration:none;font-family:'Barlow Condensed','Inter',sans-serif;font-size:var(--fs-hook1);
 font-weight:700;letter-spacing:.04em;text-transform:uppercase;border:none;border-radius:8px;
 box-shadow:0 4px 0 #a16207,0 8px 18px rgba(0,0,0,.28);
 transition:transform .18s cubic-bezier(.22,1,.36,1),box-shadow .18s cubic-bezier(.22,1,.36,1)}
.cta:hover{transform:translateY(-2px);box-shadow:0 6px 0 #a16207,0 12px 24px rgba(0,0,0,.32)}
.cta:active{transform:translateY(2px);box-shadow:0 2px 0 #a16207,0 5px 12px rgba(0,0,0,.26)}
.cta.ghost{background:transparent;color:var(--navy)!important;border:2px solid var(--navy);
 box-shadow:none;min-height:48px;font-size:var(--fs-label);letter-spacing:.07em}
.cta.ghost:hover{background:#e8ecf1;transform:none;box-shadow:none}
.hero .cta.ghost,.endband .cta.ghost{color:var(--amber-soft)!important;
 border-color:rgba(245,158,11,.6)}
.hero .cta.ghost:hover,.endband .cta.ghost:hover{background:rgba(245,158,11,.14)}
.actions{margin:var(--s3) 0 0;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
@media (prefers-reduced-motion:reduce){.cta{transition:none}.cta:hover{transform:none}}

/* ── paper content ── */
main{padding:var(--s3) 0 var(--s5)}
h2.sec{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:var(--s4) 0 var(--s2);
 font-family:'Barlow Condensed','Inter',sans-serif;font-weight:700;font-size:var(--fs-h2);color:var(--navy)}
h2.sec .lab{flex:0 1 auto;max-width:100%;overflow-wrap:anywhere;background:var(--amber);color:var(--navy);padding:4px 11px;
 font-size:var(--fs-label);line-height:1.15;letter-spacing:.12em;text-transform:uppercase;border-radius:4px}
h2.sec .rl{flex:1 1 auto;height:3px;background:var(--navy);border-radius:2px}
h2.sec:first-child{margin-top:var(--s2)}
h3{font-size:var(--fs-h3);line-height:1.2;margin:0}
p{margin:0 0 var(--s2);max-width:70ch;text-wrap:pretty}
.chip{display:inline-block;background:#eef1f5;color:var(--slate);border:1px solid #d7dee6;
 font-size:var(--fs-label);font-weight:700;letter-spacing:.07em;text-transform:uppercase;
 padding:3px 11px;border-radius:999px;white-space:nowrap;line-height:1.35}

/* hook typography: hook1 is the pull-quote, hook2 the story under an ABOUT chip */
p.hk1{font-weight:800;color:var(--navy);font-size:var(--fs-hook1);line-height:1.32;max-width:40ch;
 margin:0 0 var(--s3)}
p.abouthd{display:inline-block;max-width:none;margin:0 0 6px;background:var(--amber-soft);
 color:#7c4a03;font-family:'Barlow Condensed','Inter',sans-serif;font-size:var(--fs-eyebrow);font-weight:700;
 letter-spacing:.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;white-space:nowrap}
p.hk2{color:var(--muted);font-size:var(--fs-hook2);line-height:1.5;margin:0 0 var(--s2)}
p.why{font-size:var(--fs-why);color:#42474f}
.sitelink{display:inline-flex;align-items:center;min-height:44px;font-weight:700;
 font-size:var(--fs-body)}

/* ── where they stand card ── */
.standcard{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
ul.stands{list-style:none;padding:0;margin:0}
ul.stands li{display:flex;align-items:center;gap:12px;padding:11px 14px;
 border-top:1px solid var(--line)}
ul.stands li:first-child{border-top:0}
ul.stands li:nth-child(even){background:#fafbfc}
ul.stands img{width:26px;height:26px;flex:0 0 auto;object-fit:contain}
ul.stands .lbl{flex:1 1 auto;min-width:0;font-weight:600;font-size:var(--fs-body)}
.v{flex:0 0 auto;width:118px;text-align:center;font-size:var(--fs-eyebrow);font-weight:700;
 letter-spacing:.05em;text-transform:uppercase;padding:5px 0;border-radius:999px;line-height:1.25}
.v.agree{background:var(--slate);color:#fff;border:1px solid var(--slate)}
.v.disagree{background:#fff;color:var(--slate);border:1px solid #94a3b8}
.v.unknown{background:#eef1f5;color:var(--muted);border:1px solid #dbe1e8}

/* ── other candidates: neutral rail (nonpartisan), ringed face, chevron tile ── */
ul.cards{list-style:none;padding:0;margin:0;display:grid;gap:10px}
ul.cards li{display:flex;background:var(--card);border:1px solid var(--line);
 border-radius:12px;overflow:hidden}
.rail{flex:0 0 34px;background:var(--slate);color:#fff;display:flex;align-items:center;
 justify-content:center;font-family:'Barlow Condensed','Inter',sans-serif;font-weight:700;
 font-size:var(--fs-name)}
ul.cards details{flex:1 1 auto;min-width:0}
summary{list-style:none;cursor:pointer}
summary::-webkit-details-marker{display:none}
summary:focus{outline:none}
summary:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.oppsum{display:flex;align-items:center;gap:11px;padding:10px 12px;min-height:64px}
.oppsum:hover{background:#f8fafc}
.oppface{flex:0 0 auto;width:46px;height:46px;border-radius:50%;object-fit:cover;
 object-position:top center;background:#e7ebf0;box-shadow:0 0 0 2px #fff,0 0 0 3px var(--line)}
.oppsum .who{flex:1 1 auto;min-width:0}
.oppsum .nm{display:block;font-weight:700;font-size:var(--fs-name);color:var(--navy);line-height:1.18}
.oppsum .meta{margin-top:6px;display:flex;flex-wrap:wrap;gap:6px}
.chev{flex:0 0 auto;display:inline-flex;align-items:center;min-height:36px;padding:0 12px;
 border-radius:8px;background:var(--amber, #f5c145);color:#1a1a1a;font-family:'Barlow Condensed','Barlow',sans-serif;
 font-weight:800;font-size:var(--fs-label);letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}
.chev .chev-less{display:none}
details[open] .chev .chev-more{display:none}
details[open] .chev .chev-less{display:inline}
.oppbody{padding:var(--s2) 18px 18px;border-top:1px solid var(--line)}
.oppbody p{max-width:62ch;font-size:var(--fs-hook2)}
.oppbody p.hk1{font-size:var(--fs-hook1);line-height:1.35;margin-bottom:var(--s2)}
.oppbody p:last-child{margin-bottom:0}

/* ── directory: ordered by what's at stake, not by alphabet ──
   Each section is a native <details>; the marquee races get photo cards, everything
   else gets a compact tappable row. */
.dsec{margin:0}
.dsec>summary{list-style:none;cursor:pointer}
.dsec>summary::-webkit-details-marker{display:none}
.dsec>summary:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.dsec>summary h2.sec{margin:var(--s4) 0 var(--s2)}
.dsec:first-of-type>summary h2.sec{margin-top:var(--s2)}
.dsec .dchev{flex:0 0 auto;width:28px;height:28px;border-radius:6px;background:var(--amber);
 color:var(--navy);display:flex;align-items:center;justify-content:center;font-size:var(--fs-min);
 font-weight:800;line-height:1;transition:transform .18s cubic-bezier(.22,1,.36,1)}
.dsec[open] .dchev{transform:rotate(180deg)}
@media (prefers-reduced-motion:reduce){.dsec .dchev{transition:none}}
.dsec>summary:hover .dchev{background:var(--navy);color:var(--amber)}

/* marquee cards */
.mcards{display:grid;gap:12px;margin:0 0 var(--s3)}
.mcard{display:block;background:var(--card);border:1px solid var(--line);
 border-top:3px solid var(--navy);border-radius:12px;padding:14px}
a.mcard{text-decoration:none;color:inherit;
 transition:transform .18s cubic-bezier(.22,1,.36,1),border-color .18s}
a.mcard:hover{border-color:var(--navy);transform:translateY(-2px)}
@media (prefers-reduced-motion:reduce){a.mcard{transition:none}a.mcard:hover{transform:none}}
.faces{display:flex;padding-left:7px;margin:0 0 11px}
.faces img{width:44px;height:44px;margin-left:-7px;border-radius:50%;object-fit:cover;
 object-position:top center;background:#e7ebf0;
 box-shadow:0 0 0 2px #fff,0 0 0 4px var(--amber)}
.mname{display:block;font-family:'Barlow Condensed','Inter',sans-serif;font-weight:700;
 font-size:var(--fs-h3);line-height:1.12;text-transform:uppercase;letter-spacing:.01em;
 color:var(--navy);margin:0;text-wrap:balance}
.mname a{color:var(--navy);text-decoration:none}
.mname a:hover{text-decoration:underline}
.mmeta{display:flex;align-items:center;gap:8px;margin:6px 0 0;max-width:none;
 font-size:var(--fs-label);color:var(--muted)}
.mmeta .mchev{color:var(--navy);font-weight:800;font-size:var(--fs-h3);line-height:1}
ul.mpeople{list-style:none;padding:0;margin:11px 0 0;display:flex;flex-wrap:wrap;gap:8px}
ul.mpeople a{display:inline-flex;align-items:center;gap:9px;min-height:44px;padding:3px 12px 3px 3px;
 background:#f8fafc;border:1px solid var(--line);border-radius:999px;text-decoration:none;
 color:var(--navy);font-weight:700;font-size:var(--fs-label);line-height:1.2}
ul.mpeople a:hover{border-color:var(--navy)}
ul.mpeople img{width:38px;height:38px;flex:0 0 auto;border-radius:50%;object-fit:cover;
 object-position:top center;background:#e7ebf0;box-shadow:0 0 0 2px var(--amber)}
ul.mpeople .nophoto{display:inline-flex;align-items:center;justify-content:center;width:38px;
 height:38px;flex:0 0 auto;border-radius:50%;background:#e7ebf0;color:var(--slate);
 font-family:'Barlow Condensed','Inter',sans-serif;font-size:var(--fs-label);font-weight:700;
 box-shadow:0 0 0 2px var(--amber)}

/* compact rows */
.rows{display:grid;gap:8px;margin:0 0 var(--s3)}
.rrow{display:flex;align-items:center;gap:12px;min-height:58px;padding:10px 13px;
 background:var(--card);border:1px solid var(--line);border-radius:10px}
a.rrow{text-decoration:none;color:inherit}
a.rrow:hover{border-color:var(--navy);background:#f8fafc}
.rfaces{flex:0 0 auto;display:flex;padding-left:6px}
.rfaces>*{width:32px;height:32px;margin-left:-6px;border-radius:50%;flex:0 0 auto;
 box-shadow:0 0 0 2px #fff,0 0 0 3px var(--amber)}
.rfaces img{object-fit:cover;object-position:top center;background:#e7ebf0}
.rfaces .ini{display:flex;align-items:center;justify-content:center;background:#e7ebf0;
 color:var(--slate);font-family:'Barlow Condensed','Inter',sans-serif;font-size:var(--fs-min);
 font-weight:700;line-height:1}
.rrow .rr{flex:1 1 auto;min-width:0;overflow-wrap:anywhere}
.rrow .rn{display:block;font-weight:700;font-size:var(--fs-body);line-height:1.25;color:var(--navy)}
.rrow .rc{display:block;margin-top:3px;font-size:var(--fs-label);line-height:1.35;color:var(--muted)}
.rchev{flex:0 0 auto;color:var(--navy);font-weight:800;font-size:var(--fs-h3);line-height:1}
.rrow .pn{display:flex;flex-wrap:wrap;gap:0 14px;margin:0;max-width:none}
.rrow .pn a{display:inline-flex;align-items:center;min-height:44px;font-weight:700;
 font-size:var(--fs-body);line-height:1.25;color:var(--navy);text-decoration:none}
.rrow .pn a:hover{text-decoration:underline}
.rrow .po{margin:0;max-width:none;font-size:var(--fs-label);line-height:1.35}
.rrow .po a{color:var(--muted)}

/* the point of the page: answer the nine questions, then see who actually matches */
.midband{background:var(--card);border:1px solid var(--line);border-top:4px solid var(--amber);
 border-radius:12px;padding:var(--s3) 18px;margin:0 0 var(--s2)}
.midband h2{margin:0;font-family:'Barlow Condensed','Inter',sans-serif;font-weight:700;
 font-size:clamp(24px,5.4vw,32px);line-height:1.05;text-transform:uppercase;color:var(--navy);
 text-wrap:balance}
.midband p{margin:10px 0 0;color:var(--muted);max-width:52ch;font-size:var(--fs-body)}
.midband .actions{margin-top:var(--s2)}
.secfoot{margin:0 0 var(--s2)}
.secfoot a{display:inline-flex;align-items:center;min-height:44px;font-weight:700;
 font-size:var(--fs-label)}

/* ── prev / next ── */
.pager{display:grid;gap:10px;margin:var(--s4) 0 0}
.pager a{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;
 padding:11px 14px;text-decoration:none;min-height:44px}
.pager a:hover{border-color:var(--navy)}
.pager .dir{display:block;font-family:'Barlow Condensed','Inter',sans-serif;font-size:var(--fs-small);
 font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.pager .nm{font-weight:700;font-size:var(--fs-body);color:var(--navy)}
.pager .nx{text-align:right}

/* ── closing band + footer ── */
.endband{color:#fff;border-top:4px solid var(--amber);margin-top:var(--s5);
 background:linear-gradient(165deg,var(--navy) 0%,var(--navy-3) 100%)}
.endband .wrap{padding:var(--s4) 18px var(--s4)}
.endband h2{margin:0;font-family:'Barlow Condensed','Inter',sans-serif;font-weight:700;
 font-size:clamp(26px,6vw,36px);line-height:1;letter-spacing:-.01em;text-transform:uppercase}
.endband p{color:#ccd9ea;font-size:var(--fs-body);margin:11px 0 0;max-width:52ch}
footer.disc{background:var(--navy-3);color:#b3c3d7;font-size:var(--fs-small);line-height:1.6}
footer.disc .wrap{padding:var(--s2) 18px var(--s3)}
footer.disc a{color:#cfdcee}

@media(min-width:760px){
 :root{--fs-hook1:21px;--fs-name:22px;--fs-h2:24px;--fs-h3:22px;--fs-tile:26px}
 .wrap{padding:0 24px}
 header.bar .wrap{display:flex;align-items:center;justify-content:space-between;gap:18px;
  padding:13px 24px}
 nav.top{margin-top:0}
 header.bar img{height:38px}
 .hero .wrap{padding-top:var(--s3);padding-bottom:var(--s4)}
 .avatar{width:116px;height:116px}
 ul.cards{grid-template-columns:repeat(auto-fit,minmax(330px,1fr));align-items:start}
 .mcards{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
 .rows{grid-template-columns:1fr 1fr}
 .pager{grid-template-columns:1fr 1fr}
}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800'
         '&family=Barlow+Condensed:wght@700&display=swap" rel="stylesheet">')

# Chip nav — the current page is filled amber via aria-current.
NAV_ITEMS = [('/', 'Home'), ('/candidates/', 'All candidates'), ('/races/', 'All races')]

# Closing band + footer copy (same on every generated page).
END_TITLE = 'See who matches your views'
END_BLURB = ('Answer nine quick questions, then print the ballot for your address — '
             'free, nonpartisan, about two minutes.')
FOOTER = ('VoteYourViews.org is free and nonpartisan. Candidate information comes from public '
          'records and campaign websites. Corrections: '
          '<a href="mailto:gina@fantsimon.com">gina@fantsimon.com</a>.')
MAIN_CTA_LABEL = 'Answer 9 questions and see who matches you →'
MAIN_CTA = f'<a class="cta" href="/">{MAIN_CTA_LABEL}</a>'


def nav_html(current=''):
    links = ''
    for href, label in NAV_ITEMS:
        cur = ' aria-current="page"' if href == current else ''
        links += f'<a href="{href}"{cur}>{E(label)}</a>'
    return f'<nav class="top" aria-label="Main">{links}</nav>'


def tiles_html():
    return '<ul class="tiles">' + ''.join(
        f'<li><b>{E(a)}</b><span>{E(b)}</span></li>' for a, b in DATE_TILES) + '</ul>'


def page(title, desc, canonical, og_image, hero, body, extra_ld=(), nav_current=''):
    ld = '\n'.join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>'
                   for o in extra_ld)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/icons/Favicon.jpg" type="image/jpeg">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{og_image}">
{FONTS}
<style>{CSS}</style>
{ld}
<script>
  (function(){{try{{var q=new URLSearchParams(location.search);if(q.has('me'))localStorage.setItem('vg_me',q.get('me')==='0'?'':'1');if(localStorage.getItem('vg_me')==='1')window['ga-disable-G-LGM37W4CYE']=true;}}catch(e){{}}}})();
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-LGM37W4CYE"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-LGM37W4CYE');</script>
</head>
<body>
<header class="bar"><div class="wrap">
  <a href="/" aria-label="VoteYourViews.org home"><img src="/icons/VoteYourViews_Logo_White.png" alt="VoteYourViews.org" width="190" height="38"></a>
  {nav_html(nav_current)}
</div></header>
<section class="hero"><div class="wrap">
{hero}
</div></section>
<main><div class="wrap">
{body}
</div></main>
<section class="endband"><div class="wrap">
<h2>{E(END_TITLE)}</h2>
<p>{E(END_BLURB)}</p>
<div class="actions">{MAIN_CTA}<a class="cta ghost" href="/races/">Browse every race</a></div>
</div></section>
<footer class="disc"><div class="wrap"><p style="margin:0 0 6px;max-width:none">{E(ELECTION_LINE)}</p>{FOOTER}</div></footer>
</body>
</html>
"""


def breadcrumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}


def write(relpath, content):
    full = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)


def hooks_block(c):
    """hook1 as the pull-quote, hook2 as the story under an ABOUT <FIRST> chip.

    `summary` repeats the hooks in the sheet, so it only appears when both hooks are empty.
    """
    out = []
    if c.get('hook1'):
        out.append(f'<p class="hk1">{hook_html(c["hook1"])}</p>')
    if SHOW_HOOK2 and c.get('hook2'):
        toks = (c.get('name') or '').split()
        if toks:
            out.append(f'<p class="abouthd">About {E(toks[0])}</p>')
        out.append(f'<p class="hk2">{hook_html(c["hook2"])}</p>')
    if not c.get('hook1') and not c.get('hook2') and c.get('summary'):
        out.append(f'<p class="hk2">{hook_html(c["summary"])}</p>')
    return ''.join(out)


def sechead(label):
    return f'<h2 class="sec"><span class="lab">{E(label)}</span><span class="rl"></span></h2>'


def avatar(c, cls='avatar', size=116):
    if not c['photo']:
        return ''
    return (f'<img{f" class={cls}" if cls else ""} src="{E(c["photo"])}" alt="{E(c["name"])}" '
            f'width="{size}" height="{size}" loading="lazy">')


def opp_card(c):
    """Other-candidate disclosure: neutral rail (never party-colored — the site is
    nonpartisan), ringed face, name, party chip, chevron tile that rotates on open."""
    party = PARTY_NAME.get(c['party'], 'Independent')
    face = (f'<img class="oppface" src="{E(c["photo"])}" alt="{E(c["name"])}" '
            f'width="46" height="46" loading="lazy">') if c['photo'] else ''
    inner = hooks_block(c)
    if c.get('website'):
        inner += (f'<p><a class="sitelink" href="{E(c["website"])}" rel="nofollow noopener" '
                  f'target="_blank">Campaign website ↗</a></p>')
    inner += f'<p><a class="sitelink" href="/candidates/{c["slug"]}/">{E(c["name"])} →</a></p>'
    return (f'<li><span class="rail" aria-hidden="true">{E(party[0])}</span><details>'
            f'<summary><span class="oppsum">{face}<span class="who">'
            f'<span class="nm">{E(c["name"])}</span>'
            f'<span class="meta"><span class="chip">{E(party)}</span></span></span>'
            f'<span class="chev" aria-hidden="true"><span class="chev-more">More ▾</span><span class="chev-less">Hide ▴</span></span></span></summary>'
            f'<div class="oppbody">{inner}</div></details></li>')


def stands_card(c):
    stands = [(k, label, c['positions'][k]) for k, label in ISSUES if c['positions'].get(k)]
    if not stands:
        return ''
    rows = ''.join(
        f'<li><img src="/icons/{k}.png" alt="" aria-hidden="true" width="26" height="26">'
        f'<span class="lbl">{E(l)}</span><span class="v {v.lower()}">{E(v)}</span></li>'
        for k, l, v in stands)
    return f'<div class="standcard"><ul class="stands">{rows}</ul></div>'


# ─────────────────────────────────────────────────────────────── candidate page

def candidate_page(c, race, prev_c, next_c):
    name, office = c['name'], c['office']
    party = PARTY_NAME.get(c['party'], 'Independent')
    slug = c['slug']
    first = name.split()[0]
    canonical = f'{SITE}/candidates/{slug}/'
    og = f'{SITE}/icons/og/{slug}.png' if c['has_og'] else DEFAULT_OG
    title = f'{name} — {office} · Texas Midterm 2026 | {SITE_NAME}'
    desc = clip(f'{name}, {party} candidate for {office} on the Texas Midterm 2026 ballot, '
                f'November 3, 2026. See where they stand on nine issues.')
    cta_main = f'<a class="cta" href="/{c["pretty"]}">Compare {E(first)} to your views →</a>'

    hero = (f'<p class="crumb"><a href="/">Home</a> › <a href="/candidates/">Candidates</a> › '
            f'<a href="/races/{race["slug"]}/">{E(office)}</a> › {E(name)}</p>'
            f'<p class="kicker">VoteYourViews.org · Texas Midterm 2026</p>'
            f'<div class="idrow">{avatar(c)}<div>'
            f'<h1>{E(name)}</h1><div class="hrule"></div>'
            f'<p class="role"><span class="role-l">Candidate for {E(office)}</span><span class="party-l">{E(party)}</span></p>'
            f'</div></div>'
            f'<div class="actions">{cta_main}'
            f'<a class="cta ghost" href="/races/{race["slug"]}/">See the whole race</a></div>'
            + tiles_html())

    parts = []
    body = hooks_block(c)
    if c.get('website'):
        body += (f'<p><a class="sitelink" href="{E(c["website"])}" rel="nofollow noopener" '
                 f'target="_blank">Campaign website ↗</a></p>')
    if body:
        parts.append(sechead(f'Who {first} is') + body)
    stands = stands_card(c)
    if stands:
        parts.append(sechead('Where they stand') + stands)

    opps = [o for o in race['candidates'] if o['slug'] != slug]
    if opps:
        parts.append(sechead(f'Also on the ballot for {office}')
                     + '<p>Every candidate on this ballot line appears here, in alphabetical '
                       'order. Tap a name to read more.</p>'
                     + '<ul class="cards">' + ''.join(opp_card(o) for o in opps) + '</ul>')

    pager = []
    if prev_c:
        pager.append(f'<a href="/candidates/{prev_c["slug"]}/"><span class="dir">← Previous candidate'
                     f'</span><span class="nm">{E(prev_c["name"])}</span></a>')
    else:
        pager.append('<span></span>')
    if next_c:
        pager.append(f'<a class="nx" href="/candidates/{next_c["slug"]}/"><span class="dir">'
                     f'Next candidate →</span><span class="nm">{E(next_c["name"])}</span></a>')
    parts.append(f'<nav class="pager" aria-label="Other candidates in this race">'
                 f'{"".join(pager)}</nav>')

    person = {"@context": "https://schema.org", "@type": "Person", "name": name,
              "jobTitle": f"Candidate for {office}", "url": canonical}
    if c['photo']:
        person["image"] = abs_url(c['photo'])
    if c.get('website'):
        person["sameAs"] = [c['website']]
    crumbs = breadcrumbs([("Home", f"{SITE}/"), ("Candidates", f"{SITE}/candidates/"),
                          (office, f"{SITE}/races/{race['slug']}/"), (name, canonical)])
    return page(title, desc, canonical, og, hero, '\n'.join(parts), [person, crumbs],
                nav_current='/candidates/')


# ───────────────────────────────────────────────────────────────────── race page

def race_page(race, prev_r=None, next_r=None):
    office = race['office']
    canonical = f"{SITE}/races/{race['slug']}/"
    title = f'{office} — Texas Midterm 2026 candidates | {SITE_NAME}'
    names = ', '.join(c['name'] for c in race['candidates'][:3])
    desc = clip(f'Candidates for {office} on the Texas Midterm 2026 ballot, November 3, 2026'
                + (f': {names}.' if names else '.'))
    n = len(race['candidates'])
    hero = (f'<p class="crumb"><a href="/">Home</a> › <a href="/races/">Races</a> › {E(office)}</p>'
            f'<p class="kicker">VoteYourViews.org · Texas Midterm 2026</p>'
            f'<h1>{E(office)}</h1><div class="hrule"></div>'
            f'<p class="role">{n} candidate{"s" if n != 1 else ""} on the ballot · '
            f'Election Day November 3, 2026</p>'
            f'<div class="actions">{MAIN_CTA}'
            f'<a class="cta ghost" href="/races/">All races</a></div>' + tiles_html())

    parts = []
    if race.get('description'):
        parts.append(sechead('About this office')
                     + f'<p class="why">{hook_html(race["description"])}</p>')
    parts.append(sechead('Candidates')
                 + '<ul class="cards">' + ''.join(opp_card(c) for c in race['candidates']) + '</ul>')

    pager = []
    if prev_r:
        pager.append(f'<a href="/races/{prev_r["slug"]}/"><span class="dir">← Previous race</span>'
                     f'<span class="nm">{E(prev_r["office"])}</span></a>')
    else:
        pager.append('<span></span>')
    if next_r:
        pager.append(f'<a class="nx" href="/races/{next_r["slug"]}/"><span class="dir">Next race →'
                     f'</span><span class="nm">{E(next_r["office"])}</span></a>')
    parts.append(f'<nav class="pager" aria-label="Nearby races">{"".join(pager)}</nav>')

    crumbs = breadcrumbs([("Home", f"{SITE}/"), ("Races", f"{SITE}/races/"), (office, canonical)])
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": f"{office} candidates",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": c['name'],
                                     "url": f"{SITE}/candidates/{c['slug']}/"}
                                    for i, c in enumerate(race['candidates'])]}
    return page(title, desc, canonical, DEFAULT_OG, hero, '\n'.join(parts), [crumbs, itemlist],
                nav_current='/races/')


# ─────────────────────────────────────────────────────────────────── index pages

# The directory is ordered by what is at stake, not by the alphabet. `SECTIONS` is the
# published order; `classify()` decides which one a race belongs to, from the office name
# first and the source sheet tab (Statewide / Districts / a county tab) as the fallback.
SECTIONS = [
    ('marquee',   'The big ones',      True,  None),
    ('ushouse',   'U.S. House',        True,  'federal'),
    ('txsenate',  'Texas Senate',      False, 'state'),
    ('txhouse',   'Texas House',       False, 'state'),
    ('highcourt', 'Statewide courts',  False, 'judicial'),
    ('appeals',   'Courts of Appeals', False, 'judicial'),
    ('local',     'County & local',    False, 'county'),
    ('other',     'Other races',       False, None),
]

# Order inside "The big ones": the offices a voter recognises, in ballot order.
MARQUEE_ORDER = ['U.S. Senate', 'Governor of Texas', 'Lieutenant Governor', 'Attorney General',
                 'Comptroller of Public Accounts', 'Commissioner of General Land Office',
                 'Commissioner of Agriculture', 'Railroad Commissioner']
MARQUEE_RANK = {o: i for i, o in enumerate(MARQUEE_ORDER)}

# natural sort so District 9 lands before District 10, not after District 1
natkey = lambda s: [int(p) if p.isdigit() else p.lower() for p in re.split(r'(\d+)', s)]


def classify(office, tab):
    o = office.strip()
    if o in MARQUEE_RANK or o.startswith('State Board of Education'):
        return 'marquee'
    if o.startswith('U.S. House'):
        return 'ushouse'
    if o.startswith('TX State Senate'):
        return 'txsenate'
    if o.startswith('TX State House'):
        return 'txhouse'
    if o.startswith('TX Supreme Court') or o.startswith('Court of Criminal Appeals'):
        return 'highcourt'
    if 'Court of Appeals' in o:
        return 'appeals'
    if tab not in ('Statewide', 'Districts') or 'County' in o:
        return 'local'
    return 'other'


def section_groups(races):
    """[(label, open?, icon, [race, ...]), ...] in published order; empty sections dropped."""
    buckets = {}
    for r in races:
        buckets.setdefault(classify(r['office'], r['tab']), []).append(r)
    out = []
    for key, label, is_open, icon in SECTIONS:
        group = buckets.get(key)
        if not group:
            continue
        group.sort(key=lambda r: (MARQUEE_RANK.get(r['office'], 99), natkey(r['office']))
                   if key == 'marquee' else natkey(r['office']))
        out.append((label, is_open, icon, group))
    return out


def faces_html(race):
    imgs = ''.join(f'<img src="{E(c["photo"])}" alt="" aria-hidden="true" width="44" height="44" '
                   f'loading="lazy">' for c in race['candidates'][:5] if c['photo'])
    return f'<span class="faces">{imgs}</span>' if imgs else ''


def marquee_card(r, kind):
    n = len(r['candidates'])
    meta = f'{n} candidate{"s" if n != 1 else ""}'
    if kind == 'races':
        return (f'<a class="mcard" href="/races/{r["slug"]}/">{faces_html(r)}'
                f'<span class="mname">{E(r["office"])}</span>'
                f'<span class="mmeta">{meta}<span class="mchev" aria-hidden="true">›</span>'
                f'</span></a>')
    people = ''
    for c in r['candidates']:
        face = (f'<img src="{E(c["photo"])}" alt="" aria-hidden="true" width="38" height="38" '
                f'loading="lazy">') if c['photo'] else (
                f'<span class="nophoto" aria-hidden="true">{E(c["name"][:1])}</span>')
        people += (f'<li><a href="/candidates/{c["slug"]}/">{face}'
                   f'<span>{E(c["name"])}</span></a></li>')
    return (f'<div class="mcard"><h3 class="mname">'
            f'<a href="/races/{r["slug"]}/">{E(r["office"])}</a></h3>'
            f'<p class="mmeta">{meta}</p><ul class="mpeople">{people}</ul></div>')


def row_faces(race, size=32):
    """Overlapping faces for a compact row — a real photo, or the candidate's initial."""
    out = ''
    for c in race['candidates'][:5]:
        if c['photo']:
            out += (f'<img src="{E(c["photo"])}" alt="" aria-hidden="true" width="{size}" '
                    f'height="{size}" loading="lazy">')
        else:
            out += f'<span class="ini" aria-hidden="true">{E(c["name"][:1])}</span>'
    return f'<span class="rfaces">{out}</span>' if out else ''


def compact_row(r, kind):
    if kind == 'races':
        names = ' · '.join(E(c['name']) for c in r['candidates'])
        return (f'<a class="rrow" href="/races/{r["slug"]}/">{row_faces(r)}<span class="rr">'
                f'<span class="rn">{E(r["office"])}</span>'
                f'<span class="rc">{names}</span></span>'
                f'<span class="rchev" aria-hidden="true">›</span></a>')
    links = ''.join(f'<a href="/candidates/{c["slug"]}/">{E(c["name"])}</a>'
                    for c in r['candidates'])
    return (f'<div class="rrow">{row_faces(r)}<span class="rr"><span class="pn">{links}</span>'
            f'<p class="po"><a href="/races/{r["slug"]}/">{E(r["office"])} ›</a></p>'
            f'</span></div>')


def directory_page(races, kind, n_cands):
    if kind == 'candidates':
        canonical = f'{SITE}/candidates/'
        h1 = 'All Texas Midterm 2026 candidates'
        other = '<a class="cta ghost" href="/races/">Browse by race</a>'
    else:
        canonical = f'{SITE}/races/'
        h1 = 'All Texas Midterm 2026 races'
        other = '<a class="cta ghost" href="/candidates/">Browse by candidate</a>'
    title = f'{h1} | {SITE_NAME}'
    desc = clip(f'Every race and candidate on the Texas Midterm 2026 ballot — Election Day '
                f'November 3, 2026. {len(races)} races, {n_cands} candidates.')
    hero = (f'<p class="crumb"><a href="/">Home</a> › {E(h1)}</p>'
            f'<p class="kicker">VoteYourViews.org · Texas Midterm 2026</p>'
            f'<h1>{E(h1)}</h1><div class="hrule"></div>'
            # the point of the page: answer honestly, then discover who actually matches —
            # the surprise works in every direction, so the line never implies a right answer
            f'<p class="role"><span class="role-l">Answer nine quick questions honestly, then see '
            f'who matches your views — you may be surprised. Free, nonpartisan, about two '
            f'minutes.</span>'
            f'<span class="party-l">{len(races)} races · {n_cands} candidates</span></p>'
            f'<div class="actions">{MAIN_CTA}{other}</div>' + tiles_html())

    midband = (f'<section class="midband"><h2>{E(END_TITLE)}</h2>'
               f'<div class="actions">{MAIN_CTA}</div></section>')
    parts = []
    for label, is_open, icon, group in section_groups(races):
        marquee = label == 'The big ones'
        img = (f'<img src="{CATEGORY_IMG[icon]}" alt="" aria-hidden="true" width="30" height="30" '
               f'style="height:30px;width:auto">' if icon in CATEGORY_IMG else '')
        items = ''.join((marquee_card if marquee else compact_row)(r, kind) for r in group)
        parts.append(
            f'<details class="dsec"{" open" if is_open else ""}><summary>'
            f'<h2 class="sec">{img}<span class="lab">{E(label)}</span><span class="rl"></span>'
            f'<span class="chip">{len(group)} race{"s" if len(group) != 1 else ""}</span>'
            f'<span class="dchev" aria-hidden="true">▾</span></h2></summary>'
            f'<div class="{"mcards" if marquee else "rows"}">{items}</div>'
            f'<p class="secfoot"><a href="/">{MAIN_CTA_LABEL}</a></p></details>')
        if marquee:
            parts.append(midband)
    crumbs = breadcrumbs([("Home", f"{SITE}/"), (h1, canonical)])
    return page(title, desc, canonical, DEFAULT_OG, hero, '\n'.join(parts), [crumbs],
                nav_current=canonical.replace(SITE, ''))


# ──────────────────────────────────────────────────────────────────────── main

def main():
    skipped, seen, races = [], {}, {}
    for tab in TABS:
        for row in fetch_csv(tab):
            name = (row.get('name') or '').strip()
            office = (row.get('office') or '').strip()
            if not name:
                skipped.append(('(blank row)', 'no name'))
                continue
            if name.upper() == 'TBD':
                skipped.append((office, 'nominee still TBD'))
                continue
            if not office:
                skipped.append((name, 'no office'))
                continue
            slug = canonical_slug(name)
            if slug in seen:
                continue
            positions = {k: (row.get(k) or '').strip() for k, _ in ISSUES}
            positions = {k: v for k, v in positions.items() if v in ('Agree', 'Disagree', 'Unknown')}
            rawcat = (row.get('category') or 'state').strip().lower()
            category = {'statewide': 'state', 'local': 'county'}.get(rawcat, rawcat)
            c = {'name': name, 'office': office, 'slug': slug, 'pretty': pretty_slug(name),
                 'party': (row.get('party') or '').strip().upper(),
                 'website': (row.get('website') or '').strip(),
                 'hook1': (row.get('hook1') or '').strip(),
                 'hook2': (row.get('hook2') or '').strip(),
                 'summary': (row.get('summary') or '').strip(),
                 'photo': resolve_photo(row, COUNTY_DIR[tab]), 'positions': positions,
                 'has_og': os.path.exists(os.path.join(ROOT, 'icons', 'og', slug + '.png'))}
            seen[slug] = c
            rs = race_slug(office)
            r = races.setdefault(rs, {'office': office, 'slug': rs, 'description': '',
                                      'category': category, 'tab': tab, 'candidates': []})
            r['candidates'].append(c)
            if not r['description'] and (row.get('description') or '').strip():
                r['description'] = row['description'].strip()

    # Nonpartisan ordering: alphabetical by name inside every race — never party-first.
    for r in races.values():
        r['candidates'].sort(key=lambda c: c['name'].lower())
    race_list = sorted(races.values(),
                       key=lambda r: (CATEGORY_ORDER.index(r['category'])
                                      if r['category'] in CATEGORY_ORDER else 99,
                                      natkey(r['office'])))

    # rebuild from scratch so a dropped candidate doesn't leave a stale page behind
    for d in ('candidates', 'races'):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)

    urls = [f'{SITE}/', f'{SITE}/candidates/', f'{SITE}/races/']
    for i, r in enumerate(race_list):
        write(f'races/{r["slug"]}/index.html',
              race_page(r, race_list[i - 1] if i else None,
                        race_list[i + 1] if i + 1 < len(race_list) else None))
        urls.append(f'{SITE}/races/{r["slug"]}/')
        cands = r['candidates']
        for i, c in enumerate(cands):
            write(f'candidates/{c["slug"]}/index.html',
                  candidate_page(c, r, cands[i - 1] if i else None,
                                 cands[i + 1] if i + 1 < len(cands) else None))
            urls.append(f'{SITE}/candidates/{c["slug"]}/')
    write('candidates/index.html', directory_page(race_list, 'candidates', len(seen)))
    write('races/index.html', directory_page(race_list, 'races', len(seen)))

    body = '\n'.join(f'  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>' for u in urls)
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
                         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                         + body + '\n</urlset>\n')

    no_photo = [c['name'] for c in seen.values() if not c['photo']]
    no_text = [c['name'] for c in seen.values() if not (c['hook1'] or c['hook2'] or c['summary'])]
    no_pos = [c['name'] for c in seen.values() if not c['positions']]
    partial = [c['name'] for c in seen.values() if 0 < len(c['positions']) < len(ISSUES)]
    no_site = [c['name'] for c in seen.values() if not c['website']]
    no_og = [c['name'] for c in seen.values() if not c['has_og']]
    print(f'{len(seen)} candidate pages, {len(race_list)} race pages, 2 directory pages')
    print(f'sitemap.xml: {len(urls)} URLs (lastmod {TODAY})')
    print(f'skipped rows: {len(skipped)}')
    for reason in sorted(set(x for _, x in skipped)):
        print(f'   {sum(1 for _, x in skipped if x == reason)} × {reason}')
    print(f'data gaps — no photo: {len(no_photo)}, no hook/summary: {len(no_text)}, '
          f'no positions: {len(no_pos)}, partial positions: {len(partial)}, '
          f'no website: {len(no_site)}, no OG card: {len(no_og)}')


if __name__ == '__main__':
    main()
