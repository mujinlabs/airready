# airready

[![PyPI](https://img.shields.io/pypi/v/mujin-airready)](https://pypi.org/project/mujin-airready/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Is your website ready for AI agents and LLM crawlers?** `airready` grades any site on the
signals that decide whether ChatGPT, Claude, Perplexity & co. can find, read, and cite it —
and gives you a score, a grade, and the fixes.

```bash
pipx install mujin-airready
airready scan https://example.com
```

```
AI-readiness: https://example.com
  [----] +25 llms.txt: no /llms.txt
         → Add an /llms.txt summarizing your site for LLMs — see llmstxt.org.
  [----] +15 structured data (JSON-LD): no JSON-LD
         → Add schema.org JSON-LD so machines understand your content.
  [PASS] +8  page title: title present
  ...
  Score: 48/100  (grade D)
```

### Gate it in CI

`airready scan` exits non-zero when the site falls below a bar, so a nightly job or a
pre-deploy step can guard AI-readiness like any other check:

```bash
airready scan https://yoursite.com --min-grade B   # or --min-score 75
```

Wrapped as a GitHub Action: **[airready-action](https://github.com/mujinlabs/airready-action)**.

## What it checks

| Signal | Why it matters |
|---|---|
| **llms.txt** | The emerging standard ([llmstxt.org](https://llmstxt.org)) for telling LLMs what your site is about |
| **AI-bot policy in robots.txt** | Whether you've intentionally allowed/blocked GPTBot, ClaudeBot, Google-Extended, PerplexityBot… |
| **Structured data (JSON-LD)** | schema.org markup machines use to understand content |
| **Server-rendered content** | Many AI crawlers don't run JavaScript — an empty SPA shell is invisible to them |
| **sitemap.xml** | So crawlers find every page |
| **title / meta description / Open Graph / canonical / h1** | Core machine-readable metadata |

## Web tool & badge (self-hosted on Vercel)

This repo also ships the **AI-Readiness Grader** web tool: a URL box that grades any site
and gives you an embeddable **"AI-Ready" badge** — paste it on your site and it links back
to your full report. (`/api/scan`, `/api/badge`, `index.html`; deploys on Vercel zero-config;
the functions are self-contained and stdlib-only, so the deploy has no dependencies.)

```html
<a href="https://airready.mujinlabs.com/?url=YOURSITE">
  <img src="https://airready.mujinlabs.com/api/badge?grade=A&score=92" alt="AI-Ready: A">
</a>
```

---

Built by **[Mujin Labs](https://github.com/mujinlabs)** — tooling for the autonomous-agent era. MIT.
