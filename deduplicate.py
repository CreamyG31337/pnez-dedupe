"""Deduplicate PNEZ csv files in the input folder.

Each row is: Point, Northing, Easting, Elevation, Feature code (PNEZD).
Other column orders, e.g. PENZD, can be set with --format.
Points closer together than --tolerance (horizontal distance in file units,
0 = exact match) are treated as the same location.  By default one row is
kept per location and any differing feature codes are concatenated with "/";
pass --per-code to keep one row per location per feature code instead.
Results go to the output folder under the same filename.
"""

import argparse
import csv
from collections import defaultdict
from math import hypot
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"
CODE_SEPARATOR = "/"


def find_nearest(grid, n, e, tol, want_code):
    """Index of the closest kept point within tol of (n, e), or None.

    want_code is the upper-cased feature code to require, or None to accept
    any code.  The grid is a spatial hash with cell size tol, so a match can
    only live in the point's own cell or one of its 8 neighbours.
    """
    ix, iy = int(n // tol), int(e // tol)
    best_idx = None
    best_d = tol
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for pn, pe, pcode, idx in grid.get((ix + dx, iy + dy), ()):
                if want_code is not None and pcode != want_code:
                    continue
                d = hypot(n - pn, e - pe)
                if d <= best_d:
                    best_d = d
                    best_idx = idx
    return best_idx


def parse_format(fmt):
    """Column indices (northing, easting, code) for a format like PNEZD.

    Letters: P=point number, N=northing, E=easting, Z=elevation,
    D=description/feature code (appended automatically if omitted, so
    "PNEZ" means PNEZD).
    """
    fmt = fmt.upper()
    if "D" not in fmt:
        fmt += "D"
    if len(set(fmt)) != len(fmt) or not set(fmt) <= set("PNEZD"):
        raise argparse.ArgumentTypeError(
            f"format must be a permutation of the letters PNEZD, got {fmt!r}")
    for required in "NE":
        if required not in fmt:
            raise argparse.ArgumentTypeError(f"format is missing {required!r}")
    return fmt.index("N"), fmt.index("E"), fmt.index("D")


def dedupe_file(src, dest, tol, per_code, cols):
    idx_n, idx_e, idx_d = cols
    rows = []   # kept rows, in input order
    codes = []  # per kept row: {UPPER CODE: original casing} seen at that point
    exact = {}  # (n, e[, code]) -> kept row index, used when tol == 0
    grid = defaultdict(list)  # spatial hash of kept points, used when tol > 0
    total = 0
    multi_code = 0

    with src.open(newline="") as fin:
        for row in csv.reader(fin):
            if not row:
                continue
            total += 1
            try:
                n, e = float(row[idx_n]), float(row[idx_e])
                code = row[idx_d].strip()
            except (IndexError, ValueError):
                rows.append(row)
                codes.append(None)
                continue
            ucode = code.upper()
            if tol == 0:
                key = (n, e, ucode) if per_code else (n, e)
                idx = exact.get(key)
            else:
                idx = find_nearest(grid, n, e, tol, ucode if per_code else None)
            if idx is None:
                idx = len(rows)
                rows.append(row)
                codes.append({ucode: code})
                if tol == 0:
                    exact[key] = idx
                else:
                    grid[(int(n // tol), int(e // tol))].append((n, e, ucode, idx))
            elif not per_code and ucode not in codes[idx]:
                codes[idx][ucode] = code

    with dest.open("w", newline="") as fout:
        writer = csv.writer(fout)
        for row, seen in zip(rows, codes):
            if seen and len(seen) > 1:
                multi_code += 1
                row = row.copy()
                row[idx_d] = CODE_SEPARATOR.join(seen.values())
            writer.writerow(row)
    return total, len(rows), multi_code


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-t", "--tolerance", type=float, default=0.0,
        help="treat points within this horizontal distance as the same "
             "location (file units, default 0 = exact match)")
    p.add_argument(
        "-f", "--format", type=parse_format, default="PNEZ", metavar="ORDER",
        help="column order of the csv, a permutation of PNEZD "
             "(P=point, N=northing, E=easting, Z=elevation, D=feature code; "
             "trailing D may be omitted). Default PNEZD; PENZD is also common")
    p.add_argument(
        "--per-code", action="store_true",
        help="keep one point per location per feature code instead of "
             "flattening codes at a location")
    return p.parse_args()


def main():
    args = parse_args()
    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_files = sorted(INPUT_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No csv files found in {INPUT_DIR}")
        return
    for src in csv_files:
        total, kept, multi = dedupe_file(
            src, OUTPUT_DIR / src.name, args.tolerance, args.per_code,
            args.format)
        line = (f"{src.name}: {total} rows -> {kept} kept "
                f"({total - kept} duplicates removed)")
        if multi:
            line += (f"; {multi} points kept multiple feature codes "
                     f"({CODE_SEPARATOR}-joined)")
        print(line)


if __name__ == "__main__":
    main()
