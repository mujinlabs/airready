"""Pure evaluation: given fetched site content, compute checks + score.

All network access lives in fetch.py; this module is pure so it's fully
testable with canned content. HTML is inspected with conservative regexes
(stdlib only) — we only need presence/shape signals, not a full parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Major AI crawlers a site might allow/deny in robots.txt.
AI_BOTS = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-Web",
           "anthropic-ai", "Google-Extended", "PerplexityBot", "CCBot",
           "Bytespider", "Applebot-Extended", "Meta-ExternalAgent"]


@dataclass
class Page:
    url: str
    final_url: str = ""
    status: int = 0
    html: str = ""
    llms_txt: str | None = None      # body of /llms.txt if it's real text (not an HTML 404)
    robots_txt: str | None = None
    sitemap_xml: str | None = None


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    weight: int
    passed: bool
    detail: str
    recommendation: str


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def _visible_text_len(html: str) -> int:
    no_script = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html,
                       flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", no_script)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)


def evaluate(page: Page) -> tuple[list[Check], int]:
    html = page.html or ""
    checks: list[Check] = []

    def add(id, label, weight, passed, detail, rec):
        checks.append(Check(id, label, weight, passed, detail, rec))

    # 1. llms.txt — the headline AI-readiness signal.
    has_llms = bool(page.llms_txt and page.llms_txt.strip())
    add("llms_txt", "llms.txt", 25, has_llms,
        "found /llms.txt" if has_llms else "no /llms.txt",
        "Add an /llms.txt (and optionally /llms-full.txt) summarizing your site for LLMs — see llmstxt.org.")

    # 2. robots.txt has an explicit AI-bot policy.
    robots = page.robots_txt or ""
    ai_named = [b for b in AI_BOTS if _has(rf"User-agent:\s*{re.escape(b)}", robots)]
    add("robots_ai", "AI-bot policy in robots.txt", 12, bool(ai_named),
        f"names {len(ai_named)} AI bot(s): {', '.join(ai_named[:4])}" if ai_named
        else ("robots.txt present, no AI bots named" if robots else "no robots.txt"),
        "Declare an intentional policy for AI crawlers (GPTBot, ClaudeBot, Google-Extended, PerplexityBot) in robots.txt.")

    # 3. sitemap.xml (direct or referenced in robots).
    has_sitemap = bool(page.sitemap_xml and "<urlset" in page.sitemap_xml.lower()
                       or "<sitemapindex" in (page.sitemap_xml or "").lower()) \
        or _has(r"Sitemap:\s*http", robots)
    add("sitemap", "sitemap.xml", 8, has_sitemap,
        "sitemap found" if has_sitemap else "no sitemap.xml",
        "Publish a sitemap.xml and reference it in robots.txt so crawlers can find every page.")

    # 4. JSON-LD structured data.
    has_jsonld = _has(r'<script[^>]+type=["\']application/ld\+json["\']', html)
    add("structured_data", "structured data (JSON-LD)", 15, has_jsonld,
        "JSON-LD present" if has_jsonld else "no JSON-LD",
        "Add schema.org JSON-LD so machines understand your content (Organization, Article, Product, FAQ).")

    # 5. Server-rendered content (not an empty JS shell).
    text_len = _visible_text_len(html)
    ssr_ok = text_len >= 600
    add("ssr_content", "server-rendered content", 10, ssr_ok,
        f"{text_len} chars of text in initial HTML",
        "Serve real content in the initial HTML (SSR/SSG). Many AI crawlers don't execute JavaScript.")

    # 6. <title>
    title_ok = _has(r"<title>\s*\S+", html)
    add("title", "page title", 8, title_ok, "title present" if title_ok else "missing/empty title",
        "Give every page a unique, descriptive <title>.")

    # 7. meta description
    desc_ok = _has(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'][^"\']{10,}', html) \
        or _has(r'<meta[^>]+content=["\'][^"\']{10,}["\'][^>]+name=["\']description["\']', html)
    add("meta_description", "meta description", 8, desc_ok,
        "meta description present" if desc_ok else "no meta description",
        "Add a meta description (a concise summary crawlers and previews use).")

    # 8. Open Graph
    og_ok = _has(r'<meta[^>]+property=["\']og:(title|description)["\']', html)
    add("open_graph", "Open Graph tags", 8, og_ok, "Open Graph present" if og_ok else "no Open Graph",
        "Add og:title/og:description/og:image for rich machine + social previews.")

    # 9. canonical
    canon_ok = _has(r'<link[^>]+rel=["\']canonical["\']', html)
    add("canonical", "canonical link", 3, canon_ok, "canonical present" if canon_ok else "no canonical",
        "Add <link rel=\"canonical\"> to avoid duplicate-content ambiguity.")

    # 10. h1
    h1_ok = _has(r"<h1[\s>]", html)
    add("h1", "h1 heading", 3, h1_ok, "h1 present" if h1_ok else "no h1",
        "Use a single clear <h1> so the main topic is unambiguous.")

    score = sum(c.weight for c in checks if c.passed)
    return checks, score


def grade_for(score: int) -> str:
    return ("A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60
            else "D" if score >= 40 else "F")


@dataclass
class Report:
    url: str
    final_url: str
    status: int
    checks: list[Check] = field(default_factory=list)
    score: int = 0

    @property
    def grade(self) -> str:
        return grade_for(self.score)

    def to_dict(self) -> dict:
        return {
            "url": self.url, "final_url": self.final_url, "status": self.status,
            "score": self.score, "grade": self.grade,
            "checks": [c.__dict__ for c in self.checks],
        }


def grade_page(page: Page) -> Report:
    checks, score = evaluate(page)
    return Report(page.url, page.final_url or page.url, page.status, checks, score)
