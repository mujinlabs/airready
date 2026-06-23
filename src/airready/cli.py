"""CLI for the airready engine (also the local way to test the grader)."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import grade_page, grade_for
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

    # Prioritized fix-list: the highest-weight misses first answer the only
    # question a low scorer has — "what do I fix first for the biggest jump?"
    misses = sorted((c for c in report.checks if not c.passed),
                    key=lambda c: c.weight, reverse=True)[:3]
    if misses:
        gain = sum(c.weight for c in misses)
        projected = report.score + gain
        out.append("")
        out.append("  Top fixes (most points first):")
        for c in misses:
            out.append(f"    +{c.weight:<2} {c.label} → {c.recommendation}")
        out.append(f"    Fixing these {len(misses)} → ~{projected}/100 "
                   f"(grade {grade_for(projected)}).")
        out.append(f"    Re-run `airready scan {report.final_url}` after your "
                   f"fix to verify the score moved.")
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
