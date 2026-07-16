#!/usr/bin/env python3
"""Generate per-candidate OG share cards (1200x630 PNG) from the Google Sheet.

For every named candidate with a photo, renders a share card to icons/og/<slug>.png
and writes icons/og/manifest.json (slug -> name/office/party/description) that the
candidate-og Edge Function uses to inject per-candidate meta tags.

Usage:  python3 tools/generate-og-cards.py            # all candidates
        python3 tools/generate-og-cards.py ginahinojosa  # just one slug

Requires Google Chrome (headless render). Re-run whenever candidates/photos change.
"""
import base64, csv, io, json, os, re, subprocess, sys, tempfile, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET_ID = '1V1oaEy6ToV3LZt0et9bIWEJQbPrYZg73tDxGelhiFn8'
# Shared tabs first (three-tab architecture, July 2026) so their canonical rows win the
# per-slug dedupe over any leftover mirrored rows still sitting in the county tabs.
TABS = ['Statewide', 'Districts', 'HaysCounty', 'TravisCounty']
COUNTY_DIR = {'Statewide': 'statewide', 'Districts': 'statewide', 'HaysCounty': 'hays', 'TravisCounty': 'travis'}
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
OUT_DIR = os.path.join(ROOT, 'icons', 'og')

# Landing-grid order; tile icons live at icons/<key>.png
ISSUE_ORDER = ['reproductiveRights', 'immigration', 'affordability', 'education',
               'electionIntegrity', 'healthcare', 'socialSecurity', 'gunPolicy', 'climate']

PARTY = {
    'D': ('Democrat',   '#3b82f6', 'rgba(59,130,246,0.18)',  '#93c5fd'),
    'R': ('Republican', '#ef4444', 'rgba(239,68,68,0.18)',   '#fca5a5'),
}
PARTY_OTHER = ('Independent', '#94a3b8', 'rgba(148,163,184,0.18)', '#cbd5e1')

canonical_slug = lambda name: re.sub(r'[^a-z0-9]', '', (name or '').lower())

def photo_slug(name):
    n = unicodedata.normalize('NFKD', name)
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return re.sub(r'^-|-$', '', re.sub(r'[^a-zA-Z0-9]+', '-', n)).lower()

def b64_file(path):
    ext = path.rsplit('.', 1)[-1].lower()
    mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else 'image/png'
    with open(path, 'rb') as f:
        return f'data:{mime};base64,' + base64.b64encode(f.read()).decode()

def fetch_csv(tab):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab}'
    text = urllib.request.urlopen(url).read().decode('utf-8')
    # same sanitize as the app: drop junk trailing empty columns
    lines = [re.sub(r'(,"")+\s*$', '', l) for l in text.replace('\r', '').split('\n')]
    return list(csv.DictReader(io.StringIO('\n'.join(lines))))

def ensure_cutout(b64_data):
    """The plate design needs transparent cutouts. If a photo has no usable alpha,
    remove its background with rembg (affects the card render only, never the source file)."""
    import base64 as _b64, io as _io
    from PIL import Image
    raw = _b64.b64decode(b64_data.split(',', 1)[1])
    img = Image.open(_io.BytesIO(raw)).convert('RGBA')
    alpha = img.getchannel('A')
    # A real cutout is MOSTLY transparent around the subject. A rectangle with a stray
    # transparent corner isn't one — measure the transparent fraction, not its existence.
    hist = alpha.histogram()
    transparent_ratio = sum(hist[:32]) / (img.width * img.height)
    if transparent_ratio < 0.05:  # effectively rectangular — cut the background out
        from rembg import remove
        img = remove(img)
    # Trim transparent margins so the SUBJECT (not the file edge) pins to the gold bar
    bbox = img.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    buf = _io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + _b64.b64encode(buf.getvalue()).decode()

def resolve_photo(row, county_dir):
    url = (row.get('photo') or '').strip()
    slug = photo_slug(row['name'])
    party = (row.get('party') or 'NA').upper()
    for d in (f'{county_dir}/{party}', f'statewide/{party}'):
        local = os.path.join(ROOT, 'images', 'candidates', d, slug + '.png')
        if os.path.exists(local):
            return b64_file(local)
    if url.startswith('http'):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})).read()
            return 'data:image/png;base64,' + base64.b64encode(data).decode()
        except Exception as e:
            print(f'  ! photo fetch failed for {row["name"]}: {e}')
    return None

def first_name(name):
    return name.split()[0]

def build_html(cand, photo_b64, plate_b64):
    """Gina's plate design (icons/og-candidate-plate.png). Per-candidate pieces only: the photo
    (cutout, bottom pinned to the gold bar: 69px offset), the name (one word per line so long
    names stay BIG, sized by the longest word), and the race line (#3968A1, wraps up to 3 lines)."""
    name = cand['name']
    words = name.split()
    lines = words if len(words) >= 2 else [name]
    longest = max(len(w) for w in lines)
    # Long words (Gutierrez, Hernandez-Moreno...) drop ~20% so they never crowd the panel
    name_size = 83 if longest <= 7 else (66 if longest <= 10 else (56 if longest <= 13 else 46))
    # County offices ALWAYS split: "For Hays County" on its own line, the race below it
    m = re.match(r'^([A-Z][A-Za-z ]+?) County (.+)$', cand['office'])
    if m:
        office_line1, office_line2 = f"For {m.group(1)} County", m.group(2)
    elif ' of ' in cand['office']:
        # "Governor of Texas" -> "For Governor" / "of Texas" (same for Comptroller etc.)
        head, tail = cand['office'].split(' of ', 1)
        office_line1, office_line2 = f"For {head}", f"of {tail}"
    else:
        office_line1, office_line2 = f"For {cand['office']}", ''
    office_size = 35 if max(len(office_line1), len(office_line2)) <= 26 else 29
    office_html = f'{office_line1}<br/>{office_line2}' if office_line2 else office_line1
    name_html = '<br/>'.join(lines)
    name_color = {'R': '#B3202B', 'D': '#0A2870'}.get((cand['party'] or '').upper(), '#334155')
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<link href="https://fonts.googleapis.com/css2?family=Anton&display=swap" rel="stylesheet"/>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1200px; height:630px; overflow:hidden; position:relative; }}
.plate {{ position:absolute; inset:0; width:1200px; height:630px; }}
.photo {{ position:absolute; left:50%; transform:translateX(-56%); bottom:69px; height:490px; z-index:2;
  filter: drop-shadow(0 14px 34px rgba(0,0,0,0.45)); }}
.col {{ position:absolute; left:56px; top:92px; width:400px; z-index:3;
  display:flex; flex-direction:column; gap:24px; text-align:center; align-items:center; }}
.name {{ font-family:'Anton',sans-serif; font-size:{name_size}px; line-height:1.04; text-transform:uppercase;
  letter-spacing:0.015em; color:{name_color}; }}
.office {{ font-family:'Anton',sans-serif; font-size:{office_size}px; line-height:1.2; letter-spacing:0.05em;
  text-transform:uppercase; width:360px; color:#3968A1; }}
</style></head><body>
<img class="plate" src="{plate_b64}"/>
<img class="photo" src="{photo_b64}"/>
<div class="col">
  <div class="name">{name_html}</div>
  <div class="office">{office_html}</div>
</div>
</body></html>"""

def build_edit_html(cand, photo_b64, plate_b64):
    """Edit-invite card on Gina's party plates (DemEdit/RepEdit/IndEdit): the plate carries
    "CLICK TO EDIT YOUR PROFILE"; we add the name band (party color, Anton white, width-adaptive),
    "AT VOTEYOURVIEWS.ORG", and the candidate photo pinned bottom-right."""
    band_colors = {'D': '#2FA3DC', 'R': '#C0392B'}
    band = band_colors.get(cand['party'], '#64748B')
    # "at VoteYourViews.org" matches the plate's ink: navy for D/R, gray on the Independent plate
    at_color = '#0A2870' if cand['party'] in band_colors else '#64748B'
    name = cand['name']
    name_size = 64 if len(name) <= 14 else (52 if len(name) <= 20 else 42)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<link href="https://fonts.googleapis.com/css2?family=Anton&display=swap" rel="stylesheet"/>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1200px; height:630px; overflow:hidden; position:relative; font-family:'Anton',sans-serif; }}
.plate {{ position:absolute; inset:0; width:1200px; height:630px; }}
.photo {{ position:absolute; right:24px; bottom:0; height:560px; z-index:2;
  filter: drop-shadow(0 12px 30px rgba(0,0,0,0.35)); }}
.band {{ position:absolute; left:88px; top:330px; z-index:3; background:{band};
  padding:18px 34px; }}
.band .nm {{ color:#fff; font-size:{name_size}px; letter-spacing:0.04em; text-transform:uppercase; line-height:1; }}
.at {{ position:absolute; left:92px; top:472px; z-index:3; color:{at_color};
  font-size:38px; letter-spacing:0.05em; text-transform:uppercase; }}
</style></head><body>
<img class="plate" src="{plate_b64}"/>
<img class="photo" src="{photo_b64}"/>
<div class="band"><div class="nm">{name}</div></div>
<div class="at">at VoteYourViews.org</div>
</body></html>"""

def render(html, out):
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as f:
        f.write(html); tmp = f.name
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--window-size=1200,630', '--virtual-time-budget=8000',
                    f'--screenshot={out}', f'file://{tmp}'],
                   capture_output=True)
    os.unlink(tmp)
    return os.path.exists(out)

# Per-candidate OG photo overrides — graphics prepared specifically for the share card
# (e.g. Gina Hinojosa's stylized cutout) that should NOT replace the app's profile photo.
OG_PHOTO_OVERRIDES = {}

def main():
    only = canonical_slug(sys.argv[1]) if len(sys.argv) > 1 else None
    os.makedirs(OUT_DIR, exist_ok=True)
    plate_b64 = b64_file(os.path.join(ROOT, 'icons', 'og-candidate-plate.png'))
    edit_plates = {p: b64_file(os.path.join(ROOT, 'icons', f'{n}Edit.png')) for p, n in (('D', 'Dem'), ('R', 'Rep'), ('I', 'Ind'))}

    seen, manifest = set(), {}
    for tab in TABS:
        for row in fetch_csv(tab):
            name = (row.get('name') or '').strip()
            if not name or name.upper() == 'TBD':
                continue
            slug = canonical_slug(name)
            if slug in seen or (only and slug != only):
                continue
            seen.add(slug)
            cand = {'name': name, 'office': (row.get('office') or '').strip(),
                    'party': (row.get('party') or '').strip().upper()}
            override = OG_PHOTO_OVERRIDES.get(slug)
            photo = b64_file(os.path.join(ROOT, override)) if override else resolve_photo(row, COUNTY_DIR[tab])
            if not photo:
                print(f'  - skipped (no photo): {name}')
                continue
            try:
                photo = ensure_cutout(photo)
            except Exception as e:
                print(f'  ! cutout failed for {name} ({e}) — using photo as-is')
            ok = render(build_html(cand, photo, plate_b64), os.path.join(OUT_DIR, slug + '.png'))
            ok_edit = render(build_edit_html(cand, photo, edit_plates.get(cand['party'], edit_plates['I'])), os.path.join(OUT_DIR, slug + '-edit.png'))
            print(f'  {"✓" if ok else "✗"} {name} -> og/{slug}.png {"+ edit card" if ok_edit else "(edit card FAILED)"}')
            if ok:
                manifest[slug] = {'name': name, 'office': cand['office'], 'party': cand['party']}
    if not only:
        with open(os.path.join(OUT_DIR, 'manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=1)
        print(f'{len(manifest)} cards + manifest.json written to icons/og/')

if __name__ == '__main__':
    main()
