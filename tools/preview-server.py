#!/usr/bin/env python3
"""No-cache static server for local preview.

Plain `python3 -m http.server` lets the browser cache assets, which is why the
preview panel kept showing a STALE header (a cached 404 / old image) even after
the files were fixed. This server sends no-store on every response so every
refresh is guaranteed fresh — no `?v=` cache-busting needed.

Usage: preview-server.py [PORT] [DIRECTORY]
"""
import sys, os, http.server, socketserver

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8761
DIRECTORY = sys.argv[2] if len(sys.argv) > 2 else '.'


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # SPA fallback: clean per-candidate URLs like /JamesTalarico have no real file, so serve the app.
        rel = self.path.split('?', 1)[0].split('#', 1)[0]
        if not os.path.exists(self.translate_path(self.path)) and '.' not in os.path.basename(rel):
            self.path = '/index.html'
        return super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', PORT), NoCacheHandler) as httpd:
    print(f'No-cache preview server on :{PORT} serving {DIRECTORY}')
    httpd.serve_forever()
