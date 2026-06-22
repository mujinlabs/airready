"""Vercel serverless function: GET /api/scan?url=... -> JSON grade.

The engine is installed from PyPI (requirements.txt: mujin-airready), so this
function just imports and calls it.
"""

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from airready.core import grade_page
from airready.fetch import fetch_site


class handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        url = (q.get("url") or [""])[0].strip()
        if not url:
            return self._send(400, {"error": "missing ?url="})
        try:
            page = fetch_site(url, timeout=10)
        except Exception as e:  # noqa: BLE001
            return self._send(502, {"error": f"fetch failed: {e}"})
        if page.status == 0:
            return self._send(502, {"error": "could not fetch the site (DNS/timeout/blocked)"})
        self._send(200, grade_page(page).to_dict())
