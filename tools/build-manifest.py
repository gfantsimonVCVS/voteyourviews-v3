#!/usr/bin/env python3
"""Scan images/candidates/ and write manifest.json (list of available photo paths,
relative to images/candidates/). The app fetches this to know which candidates have a
self-hosted photo. Re-run after adding/changing photos:  python3 tools/build-manifest.py
"""
import json, os
from pathlib import Path

root = Path(__file__).resolve().parent.parent / "images" / "candidates"
paths = sorted(
    str(p.relative_to(root)).replace(os.sep, "/")
    for p in root.rglob("*.png")
)
out = root / "manifest.json"
out.write_text(json.dumps(paths, indent=0))
print(f"Wrote {out} with {len(paths)} photos")
for d in sorted({p.split('/')[0]+'/'+p.split('/')[1] for p in paths if '/' in p}):
    n = sum(1 for p in paths if p.startswith(d+'/'))
    print(f"  {d}: {n}")
