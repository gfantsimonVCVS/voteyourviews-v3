#!/usr/bin/env python3
"""
photo-machine.py — VoteYourViews candidate photo pipeline (v1, Process stage)

Per the spec (Docs/Candidate-Photo-Pipeline-Spec.md). This v1 does the
PROCESS + SELF-HOST part on photos that already have a source URL:
  download -> background removal (rembg) -> center on subject -> square crop
  -> resize 512x512 transparent PNG -> save to images/candidates/<county>/<slug>.png

County-agnostic: the county is just --county <name>. Reuse for any county.

It does NOT (yet) write paths back to the sheet or source missing photos
(Ballotpedia/self-submission) — those are separate, later stages. This run is
safe: it only reads the published sheet and writes local PNG files.

Usage:
  python3 photo-machine.py --county hays --party R          # first batch
  python3 photo-machine.py --county hays                    # all parties
  python3 photo-machine.py --county travis --limit 5        # smoke test

Requires: rembg, Pillow, requests  (pip3 install rembg Pillow requests)
"""
import argparse, csv, io, re, sys, unicodedata, urllib.request
from pathlib import Path

SHEET_ID = "1V1oaEy6ToV3LZt0et9bIWEJQbPrYZg73tDxGelhiFn8"
GVIZ = "https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={tab}"
OUT_SIZE = 512          # final square px
PAD = 0.12             # headroom padding around the subject (fraction of bbox)

def tab_for(county):   # county arg -> sheet tab name
    # Shared tabs (three-tab architecture, July 2026): --county statewide | districts
    if county.lower() in ("statewide", "districts"): return county[:1].upper() + county[1:].lower()
    return county[:1].upper() + county[1:].lower() + "County"

def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s

def gdrive_direct(url):
    # normalize Google Drive share/lh3 links to a direct-download form
    m = re.search(r"/d/([A-Za-z0-9_-]+)", url) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    return url

def fetch(url, as_image=False):
    # only normalize Google-Drive links for actual image downloads, never for the sheet URL
    target = gdrive_direct(url) if as_image else url
    req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0 VYV-photo-machine"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def load_rows(tab):
    url = GVIZ.format(sid=SHEET_ID, tab=tab)
    data = fetch(url).decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(data)))
    hdr = [c.strip().lower() for c in rows[0]]
    idx = {k: hdr.index(k) for k in ("office", "name", "party", "photo")}
    out = []
    for r in rows[1:]:
        if len(r) > idx["name"] and r[idx["name"]].strip():
            out.append({k: (r[idx[k]].strip() if len(r) > idx[k] else "") for k in idx})
    return out

_SESSION = None
def _session(model):
    global _SESSION
    if _SESSION is None:
        from rembg import new_session
        _SESSION = new_session(model)
    return _SESSION

def process(img_bytes, model="u2net_human_seg"):
    """rembg cut-out -> tight crop to subject -> square with padding -> 512 PNG.
    Default model = u2net_human_seg (human segmentation): robust against erasing
    light clothing on a light background (u2net ghosted shirts/robes)."""
    from rembg import remove
    from PIL import Image
    cut = remove(img_bytes, session=_session(model))          # -> PNG bytes w/ alpha
    im = Image.open(io.BytesIO(cut)).convert("RGBA")
    bbox = im.split()[3].getbbox()                            # alpha bounding box = the subject
    if bbox:
        im = im.crop(bbox)
    w, h = im.size
    side = int(max(w, h) * (1 + PAD))                         # square canvas + headroom
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))    # transparent
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)  # center the subject
    return canvas.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--county", required=True)
    ap.add_argument("--party", help="filter to one party (e.g. R)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()

    tab = tab_for(args.county)
    rows = load_rows(tab)
    if args.party:
        rows = [r for r in rows if r["party"].upper() == args.party.upper()]
    rows = [r for r in rows if r["photo"]]                    # only ones with a source URL
    if args.limit:
        rows = rows[: args.limit]

    # Statewide AND district candidates share images/candidates/statewide/ — the app looks
    # in <county>/ first then falls back to statewide/, and district races are cross-county.
    photo_dir = "statewide" if args.county.lower() in ("statewide", "districts") else args.county.lower()
    base_dir = Path(args.repo) / "images" / "candidates" / photo_dir
    print(f"Processing {len(rows)} photos from {tab} -> {base_dir}/<party>/")

    ok, fail = 0, []
    for r in rows:
        party = (r["party"] or "NA").strip().upper() or "NA"   # photos live in per-party folders
        out_dir = base_dir / party
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = slugify(r["name"])
        try:
            png = process(fetch(r["photo"], as_image=True))
            dest = out_dir / f"{slug}.png"
            png.save(dest)
            ok += 1
            print(f"  ✅ {r['name']:26} -> {party}/{dest.name}")
        except Exception as e:
            fail.append((r["name"], str(e)))
            print(f"  ❌ {r['name']:26} {e}")

    print(f"\nDone: {ok} ok, {len(fail)} failed.")
    for n, e in fail:
        print(f"   FAILED {n}: {e}")

if __name__ == "__main__":
    main()
