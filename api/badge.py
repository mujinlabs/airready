"""Vercel serverless function: GET /api/badge?grade=A&score=92 -> SVG badge.

Static (renders from params, no scan) so it's fast and embeddable. The result
page wraps it in a link back to the full report — that link is the backlink.
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

COLORS = {"A": "#2ea44f", "B": "#3fb950", "C": "#bf8700",
          "D": "#e8590c", "F": "#cf222e", "?": "#6e7781"}


def make_svg(grade: str, score: str) -> str:
    grade = (grade or "?")[:1].upper()
    if grade not in COLORS:
        grade = "?"
    right = grade + (f" {score}" if score.isdigit() else "")
    color = COLORS[grade]
    lw = 60
    rw = 26 + len(right) * 7
    w = lw + rw
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" '
        f'aria-label="AI-Ready: {right}">'
        f'<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" '
        f'stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>'
        f'<rect rx="3" width="{w}" height="20" fill="#444"/>'
        f'<rect rx="3" x="{lw}" width="{rw}" height="20" fill="{color}"/>'
        f'<rect rx="3" width="{w}" height="20" fill="url(#s)"/>'
        f'<g fill="#fff" text-anchor="middle" '
        f'font-family="Verdana,DejaVu Sans,Geneva,sans-serif" font-size="11">'
        f'<text x="{lw/2:.0f}" y="14">AI-Ready</text>'
        f'<text x="{lw + rw/2:.0f}" y="14">{right}</text>'
        f'</g></svg>'
    )


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        grade = (q.get("grade") or ["?"])[0]
        score = (q.get("score") or [""])[0]
        body = make_svg(grade, score).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
