"""Tests for the CI gate (`--min-score` / `--min-grade`). No network: the
gate is a pure function over an already-graded Report."""

from airready.core import Report
from airready.cli import gate


def _report(score):
    return Report("https://x.example", "https://x.example", 200, [], score)


def test_no_thresholds_always_passes():
    assert gate(_report(11), None, None) == (0, [])


def test_min_score_pass_and_fail():
    code, msgs = gate(_report(82), 75, None)   # B-grade site, require 75
    assert code == 0 and msgs == []
    code, msgs = gate(_report(48), 75, None)   # D-grade site, require 75
    assert code == 1 and "below --min-score 75" in msgs[0]


def test_min_grade_uses_rank_not_string_compare():
    # 'F' < 'B' as a CI rule even though "F" > "B" lexically.
    code, msgs = gate(_report(30), None, "B")  # F site, require >= B
    assert code == 1 and "below --min-grade B" in msgs[0]
    code, _ = gate(_report(92), None, "B")     # A site, require >= B
    assert code == 0


def test_both_thresholds_report_each_failure():
    code, msgs = gate(_report(20), 60, "C")    # fails both
    assert code == 1 and len(msgs) == 2


def test_boundary_is_inclusive():
    # score exactly at the threshold passes; one below fails.
    assert gate(_report(75), 75, None)[0] == 0
    assert gate(_report(74), 75, None)[0] == 1
