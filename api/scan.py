"""Vercel serverless function: GET /api/scan?url=... -> JSON grade.

Self-contained (stdlib only) so the deploy has NO external dependency and no
bundling risk. The same logic also lives in the `airready` package (CLI); keep
them in sync when the checks change.
"""

import json
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urljoin, urlparse, parse_qs

UA = "Mozilla/5.0 (compatible; airready/0.1; +https://github.com/mujinlabs/airready)"
AI_BOTS = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-Web",
           "anthropic-ai", "Google-Extended", "PerplexityBot", "CCBot",
           "Bytespider", "Applebot-Extended", "Meta-ExternalAgent"]


def _get(url, timeout=6, max_bytes=2_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(max_bytes)
            charset = r.headers.get_content_charset() or "utf-8"
            return r.status, r.geturl(), raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, url, None
    except (urllib.error.URLError, OSError, ValueError):
        return 0, url, None


def _has(pat, text):
    return re.search(pat, text, re.IGNORECASE) is not None


def _looks_html(t):
    h = (t or "")[:512].lower()
    return "<!doctype html" in h or "<html" in h


def _visible_len(html):
    no = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    return len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", no)).strip())


def _grade(score):
    return ("A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60
            else "D" if score >= 40 else "F")


def grade_url(url):
    if not urlparse(url).scheme:
        url = "https://" + url
    status, final_url, html = _get(url)
    if status == 0:
        return None
    html = html or ""
    base = final_url or url
    s, _, llms = _get(urljoin(base, "/llms.txt"))
    llms = llms if (s == 200 and llms and not _looks_html(llms)) else None
    s, _, robots = _get(urljoin(base, "/robots.txt"))
    robots = robots if (s == 200 and robots and not _looks_html(robots)) else ""
    s, _, sm = _get(urljoin(base, "/sitemap.xml"))
    has_sitemap = bool(sm and ("<urlset" in sm.lower() or "<sitemapindex" in sm.lower())) \
        or _has(r"Sitemap:\s*http", robots)

    ai_named = [b for b in AI_BOTS if _has(rf"User-agent:\s*{re.escape(b)}", robots)]
    text_len = _visible_len(html)
    checks = [
        ("llms_txt", "llms.txt", 25, bool(llms and llms.strip()),
         "found /llms.txt" if llms else "no /llms.txt",
         "Add an /llms.txt summarizing your site for LLMs — see llmstxt.org."),
        ("robots_ai", "AI-bot policy in robots.txt", 12, bool(ai_named),
         f"names {len(ai_named)} AI bot(s)" if ai_named else ("robots.txt present, no AI bots named" if robots else "no robots.txt"),
         "Declare an intentional policy for AI crawlers (GPTBot, ClaudeBot, Google-Extended, PerplexityBot) in robots.txt."),
        ("sitemap", "sitemap.xml", 8, has_sitemap,
         "sitemap found" if has_sitemap else "no sitemap.xml",
         "Publish a sitemap.xml and reference it in robots.txt."),
        ("structured_data", "structured data (JSON-LD)", 15,
         _has(r'<script[^>]+type=["\']application/ld\+json["\']', html),
         "JSON-LD present" if _has(r'application/ld\+json', html) else "no JSON-LD",
         "Add schema.org JSON-LD (Organization, Article, Product, FAQ)."),
        ("ssr_content", "server-rendered content", 10, text_len >= 600,
         f"{text_len} chars of text in initial HTML",
         "Serve real content in the initial HTML (SSR/SSG); many AI crawlers don't run JavaScript."),
        ("title", "page title", 8, _has(r"<title>\s*\S+", html),
         "title present" if _has(r"<title>\s*\S+", html) else "missing/empty title",
         "Give every page a unique, descriptive <title>."),
        ("meta_description", "meta description", 8,
         _has(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'][^"\']{10,}', html) or _has(r'<meta[^>]+content=["\'][^"\']{10,}["\'][^>]+name=["\']description["\']', html),
         "meta description present" if _has(r'name=["\']description["\']', html) else "no meta description",
         "Add a meta description."),
        ("open_graph", "Open Graph tags", 8, _has(r'<meta[^>]+property=["\']og:(title|description)["\']', html),
         "Open Graph present" if _has(r'property=["\']og:', html) else "no Open Graph",
         "Add og:title/og:description/og:image."),
        ("canonical", "canonical link", 3, _has(r'<link[^>]+rel=["\']canonical["\']', html),
         "canonical present" if _has(r'rel=["\']canonical', html) else "no canonical",
         "Add <link rel=\"canonical\">."),
        ("h1", "h1 heading", 3, _has(r"<h1[\s>]", html),
         "h1 present" if _has(r"<h1[\s>]", html) else "no h1",
         "Use a single clear <h1>."),
    ]
    score = sum(w for (_id, _l, w, p, _d, _r) in checks if p)
    return {
        "url": url, "final_url": final_url or url, "status": status,
        "score": score, "grade": _grade(score),
        "checks": [{"id": i, "label": l, "weight": w, "passed": p, "detail": d, "recommendation": r}
                   for (i, l, w, p, d, r) in checks],
    }


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
            result = grade_url(url)
        except Exception as e:  # noqa: BLE001
            return self._send(502, {"error": f"failed: {e}"})
        if result is None:
            return self._send(502, {"error": "could not fetch the site (DNS/timeout/blocked)"})
        self._send(200, result)
