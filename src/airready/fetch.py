"""Network fetching: build a Page from a live URL (stdlib urllib)."""

from __future__ import annotations

import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

from .core import Page

UA = "Mozilla/5.0 (compatible; airready/0.1; +https://github.com/mujinlabs/airready)"


def _get(url: str, timeout: float = 12.0, max_bytes: int = 2_000_000):
    """Return (status, final_url, text, content_type) or (status, url, None, '')."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(max_bytes)
            ctype = r.headers.get("Content-Type", "")
            charset = r.headers.get_content_charset() or "utf-8"
            return r.status, r.geturl(), raw.decode(charset, errors="replace"), ctype
    except urllib.error.HTTPError as e:
        return e.code, url, None, ""
    except (urllib.error.URLError, OSError, ValueError):
        return 0, url, None, ""


def _looks_like_html(text: str) -> bool:
    head = (text or "")[:512].lower()
    return "<!doctype html" in head or "<html" in head


def normalize_url(url: str) -> str:
    if not urlparse(url).scheme:
        return "https://" + url
    return url


def fetch_site(url: str, timeout: float = 12.0) -> Page:
    url = normalize_url(url)
    status, final_url, html, _ = _get(url, timeout=timeout)
    page = Page(url=url, final_url=final_url or url, status=status, html=html or "")

    base = final_url or url
    # /llms.txt — only count it if it's real text, not an SPA's HTML 404.
    s, _, body, _ = _get(urljoin(base, "/llms.txt"), timeout=timeout)
    if s == 200 and body and not _looks_like_html(body):
        page.llms_txt = body

    s, _, body, _ = _get(urljoin(base, "/robots.txt"), timeout=timeout)
    if s == 200 and body and not _looks_like_html(body):
        page.robots_txt = body

    s, _, body, _ = _get(urljoin(base, "/sitemap.xml"), timeout=timeout)
    if s == 200 and body and ("<urlset" in body.lower() or "<sitemapindex" in body.lower()):
        page.sitemap_xml = body

    return page
