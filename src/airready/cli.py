"""CLI for the airready engine (also the local way to test the grader)."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import grade_page
from .fetch import fetch_site


def _utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def render(report) -> str:
    out = [f"AI-readiness: {report.final_url}", ""]
    for c in report.checks:
        mark = "PASS" if c.passed else "----"
        out.append(f"  [{mark}] +{c.weight:<2} {c.label}: {c.detail}")
        if not c.passed:
            out.append(f"          → {c.recommendation}")
    out.append("")
    out.append(f"  Score: {report.score}/100  (grade {report.grade})")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    _utf8()
    parser = argparse.ArgumentParser(
        prog="airready",
        description="Grade how ready a website is for AI agents & LLM crawlers.")
    parser.add_argument("--version", action="version", version=f"airready {__version__}")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("scan", help="grade a URL")
    p.add_argument("url", help="website URL")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--timeout", type=float, default=12.0)

    args = parser.parse_args(argv)
    if args.command != "scan":
        parser.print_help()
        return 0

    page = fetch_site(args.url, timeout=args.timeout)
    if page.status == 0:
        print(f"error: could not fetch {args.url}", file=sys.stderr)
        return 2
    report = grade_page(page)
    print(json.dumps(report.to_dict(), indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
