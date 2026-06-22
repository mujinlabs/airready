"""Pure tests for the airready evaluation (no network)."""

from airready.core import Page, evaluate, grade_page, grade_for

GOOD_HTML = """<!doctype html><html><head>
<title>Acme — widgets that work</title>
<meta name="description" content="Acme builds durable widgets for makers everywhere.">
<meta property="og:title" content="Acme">
<meta property="og:description" content="widgets">
<link rel="canonical" href="https://acme.example/">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization"}</script>
</head><body><h1>Acme</h1>
<p>%s</p></body></html>""" % ("Acme makes the best widgets. " * 40)

EMPTY_SPA = '<!doctype html><html><head><title></title></head><body><div id="root"></div></body></html>'


def _ids_passed(page):
    checks, score = evaluate(page)
    return {c.id for c in checks if c.passed}, score


def test_well_optimized_site_scores_high():
    page = Page("https://acme.example", html=GOOD_HTML,
                llms_txt="# Acme\nWidgets.\n",
                robots_txt="User-agent: GPTBot\nAllow: /\nSitemap: https://acme.example/sitemap.xml",
                sitemap_xml="<urlset><url><loc>https://acme.example/</loc></url></urlset>")
    passed, score = _ids_passed(page)
    assert {"llms_txt", "robots_ai", "sitemap", "structured_data", "ssr_content",
            "title", "meta_description", "open_graph", "canonical", "h1"} <= passed
    assert score >= 90
    assert grade_page(page).grade == "A"


def test_bare_spa_scores_low():
    page = Page("https://spa.example", html=EMPTY_SPA)
    passed, score = _ids_passed(page)
    assert "llms_txt" not in passed
    assert "structured_data" not in passed
    assert "ssr_content" not in passed
    assert score < 40
    assert grade_page(page).grade == "F"


def test_llms_txt_is_weighted_heaviest():
    base = Page("https://x.example", html=EMPTY_SPA)
    with_llms = Page("https://x.example", html=EMPTY_SPA, llms_txt="# X\ncontent")
    _, s0 = _ids_passed(base)
    _, s1 = _ids_passed(with_llms)
    assert s1 - s0 == 25


def test_robots_ai_detection_specific_bots():
    page = Page("https://x.example", html=EMPTY_SPA,
                robots_txt="User-agent: ClaudeBot\nDisallow:\nUser-agent: PerplexityBot\nAllow: /")
    passed, _ = _ids_passed(page)
    assert "robots_ai" in passed


def test_robots_without_ai_bots_does_not_pass():
    page = Page("https://x.example", html=EMPTY_SPA, robots_txt="User-agent: *\nDisallow: /private")
    passed, _ = _ids_passed(page)
    assert "robots_ai" not in passed


def test_grade_boundaries():
    assert grade_for(90) == "A" and grade_for(75) == "B" and grade_for(60) == "C"
    assert grade_for(40) == "D" and grade_for(39) == "F"
