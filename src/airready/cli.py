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


# A>B>C>D>F — higher rank is better, so a CI gate can ask "no worse than B".
_GRADE_RANK = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def gate(report, min_score, min_grade):
    """Evaluate CI thresholds against a graded report.

    Returns (exit_code, messages). exit_code is 1 (fail the build) if the
    site scores below --min-score or grades below --min-grade, else 0. Pure
    so it's testable without a network fetch.
    """
    msgs = []
    if min_score is not None and report.score < min_score:
        msgs.append(f"score {report.score}/100 is below --min-score {min_score}")
    if min_grade and _GRADE_RANK[report.grade] < _GRADE_RANK[min_grade]:
        msgs.append(f"grade {report.grade} is below --min-grade {min_grade}")
    return (1 if msgs else 0, msgs)


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
    # CI gate: exit 1 when the live site regresses below a threshold, so a
    # nightly/deploy workflow can guard AI-readiness like any other check.
    p.add_argument("--min-score", type=int, default=None, metavar="N",
                   help="exit 1 if the score is below N (0-100)")
    p.add_argument("--min-grade", choices=list(_GRADE_RANK), default=None,
                   help="exit 1 if the grade is below this (A best, F worst)")

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
    code, msgs = gate(report, args.min_score, args.min_grade)
    for m in msgs:
        print(f"airready: {m}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
