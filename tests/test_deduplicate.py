"""Tests for deduplicate.py on small synthetic CSVs.  Run from the repo folder:  python -m pytest"""
import argparse
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import deduplicate as dd  # noqa: E402

PNEZD = dd.parse_format("PNEZD")


def run(tmp_path, rows, tol=0.0, per_code=False, cols=PNEZD):
    src, dest = tmp_path / "in.csv", tmp_path / "out.csv"
    with src.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    stats = dd.dedupe_file(src, dest, tol, per_code, cols)
    with dest.open(newline="") as f:
        return stats, list(csv.reader(f))


def test_exact_duplicates_removed_codes_flattened(tmp_path):
    rows = [["1", "100.000", "200.000", "5.0", "TOR"],
            ["2", "100.000", "200.000", "5.1", "og"],
            ["3", "100.000", "200.000", "5.2", "TOR"],     # same code again: not repeated
            ["4", "101.000", "200.000", "5.0", "TOR"]]
    (total, kept, multi), out = run(tmp_path, rows)
    assert (total, kept, multi) == (4, 2, 1)
    assert out[0] == ["1", "100.000", "200.000", "5.0", "TOR/og"]   # first row kept, codes joined
    assert out[1][0] == "4"


def test_codes_compare_case_insensitively(tmp_path):
    (_, kept, multi), out = run(tmp_path, [["1", "1", "2", "0", "Tor"], ["2", "1", "2", "0", "TOR"]])
    assert kept == 1 and multi == 0 and out[0][4] == "Tor"


def test_per_code_keeps_one_row_per_code(tmp_path):
    rows = [["1", "1", "2", "0", "TOR"], ["2", "1", "2", "0", "OG"], ["3", "1", "2", "0", "tor"]]
    (_, kept, multi), out = run(tmp_path, rows, per_code=True)
    assert kept == 2 and multi == 0 and [r[0] for r in out] == ["1", "2"]


def test_tolerance_merges_nearby_points(tmp_path):
    rows = [["1", "100.000", "200.000", "0", "A"],
            ["2", "100.0008", "200.0005", "0", "A"],       # 0.94 mm away
            ["3", "100.0030", "200.000", "0", "A"]]        # 3 mm away
    assert run(tmp_path, rows, tol=0.001)[0][1] == 2
    assert run(tmp_path, rows, tol=0.0)[0][1] == 3


def test_tolerance_across_grid_cell_boundary(tmp_path):
    # 0.9 mm apart but in different 1 mm hash cells: the neighbour search must still find it
    rows = [["1", "0.0995", "0", "0", "A"], ["2", "0.1004", "0", "0", "A"]]
    assert run(tmp_path, rows, tol=0.001)[0][1] == 1


def test_penzd_order(tmp_path):
    cols = dd.parse_format("PENZ")
    rows = [["1", "200", "100", "0", "A"], ["2", "200", "100", "0", "B"]]
    (_, kept, _), out = run(tmp_path, rows, cols=cols)
    assert kept == 1 and out[0][4] == "A/B"


def test_header_and_bad_rows_pass_through(tmp_path):
    rows = [["P", "N", "E", "Z", "D"], ["1", "1", "2", "0", "A"], ["short"], ["2", "1", "2", "0", "A"]]
    (total, kept, _), out = run(tmp_path, rows)
    assert total == 4 and kept == 3 and out[0] == rows[0] and out[2] == ["short"]


def test_parse_format():
    assert dd.parse_format("PNEZD") == (1, 2, 4)
    assert dd.parse_format("penz") == (2, 1, 4)
    for bad in ("PNNEZ", "PXEZ", "PEZD"):
        with pytest.raises(argparse.ArgumentTypeError):
            dd.parse_format(bad)
