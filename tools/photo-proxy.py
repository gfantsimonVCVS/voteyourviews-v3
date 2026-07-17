#!/usr/bin/env python3
"""
photo-proxy.py — local helper for the photo tool's "Get missing photos".

Source: Searlo (Google-results SERP API, image search) — one key, no Google Cloud / CSE / org.
Flow: candidate name -> Searlo top image results -> FACE GATE (must be exactly one face;
rejects blobs/logos/group shots/NSFW) -> rembg background removal -> square 512 PNG.
The tool fetches http://localhost:8770/find?name=... per missing candidate; you still verify.

Config: tools/photo-proxy.config.json = { "searlo_key": "sk_..." }  (gitignored)
RUN:  PATH="$HOME/Library/Python/3.9/bin:$PATH" python3 tools/photo-proxy.py
Requires: rembg, Pillow, opencv (all already installed with rembg).
"""
import io, os, json, urllib.request, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8770
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_cfg = json.load(open(os.path.join(HERE, "photo-proxy.config.json")))
SEARLO_KEY = _cfg.get("searlo_key")

def _get(url, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if headers: h.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout).read()

def searlo_image_links(name, site=""):
    # Gina's proven manual query: just "<name> Texas" — the extra word "candidate"
    # drags in race coverage and opponents.
    q = f"{name} Texas"
    url = "https://api.searlo.tech/api/v1/search/images?" + urllib.parse.urlencode({"q": q, "limit": 10, "safe": "active"})
    data = json.loads(_get(url, headers={"x-api-key": SEARLO_KEY, "Accept": "application/json"}))
    imgs = [im for im in data.get("images", []) if im.get("imageUrl")]
    # Rank like a human: results that NAME the candidate or come from their own
    # site / Ballotpedia beat whatever happens to be first.
    name_tokens = [t for t in name.lower().split() if len(t) > 2]
    site_dom = site.lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    TRUSTED = ["ballotpedia.org", "votesmart.org", "wikipedia.org", "lwv.org"]
    def score(im):
        meta = " ".join(str(im.get(k, "")) for k in ("title", "source", "sourceUrl", "pageUrl", "link")).lower()
        s = sum(2 for t in name_tokens if t in meta)          # candidate actually named
        if site_dom and site_dom in meta: s += 5              # their own campaign site
        if any(d in meta for d in TRUSTED): s += 3            # neutral reference sites
        return s
    imgs.sort(key=score, reverse=True)
    return [im["imageUrl"] for im in imgs]

_cascade = None
def one_face(raw):
    """True only if the image has exactly one detectable face (rejects junk/group/NSFW-ish)."""
    global _cascade
    import cv2, numpy as np
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _cascade.detectMultiScale(gray, 1.1, 6, minSize=(60, 60))
    return len(faces) == 1

_session = None
def process(raw):
    global _session
    from rembg import remove, new_session
    from PIL import Image
    if _session is None:
        _session = new_session("u2net_human_seg")
    im = Image.open(io.BytesIO(remove(raw, session=_session))).convert("RGBA")
    bb = im.split()[3].getbbox()
    if bb: im = im.crop(bb)
    w, h = im.size; side = int(max(w, h) * 1.12)
    c = Image.new("RGBA", (side, side), (0, 0, 0, 0)); c.paste(im, ((side - w) // 2, (side - h) // 2), im)
    out = io.BytesIO(); c.resize((512, 512), Image.LANCZOS).save(out, "PNG"); return out.getvalue()

class H(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
        if body: self.wfile.write(body)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/health":
            return self._send(200, "application/json", b'{"ok":true}')
        if u.path != "/find":
            return self._send(404, "text/plain", b"not found")
        qs = urllib.parse.parse_qs(u.query)
        name = (qs.get("name", [""])[0]).strip()
        site = (qs.get("site", [""])[0]).strip()
        try:
            tried = 0
            for link in searlo_image_links(name, site):
                if tried >= 8: break
                tried += 1
                try:
                    raw = _get(link, timeout=20)
                    if not one_face(raw):      # FACE GATE — only clean single-face headshots pass
                        continue
                    return self._send(200, "image/png", process(raw))
                except Exception:
                    continue
            raise Exception("no single-face headshot found in results")
        except Exception as e:
            self._send(502, "application/json", json.dumps({"error": str(e)}).encode())
    def log_message(self, *a): pass

if __name__ == "__main__":
    if not SEARLO_KEY:
        raise SystemExit("Missing searlo_key in tools/photo-proxy.config.json")
    print(f"Photo proxy (Searlo + face-gate) running on http://localhost:{PORT}  (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
