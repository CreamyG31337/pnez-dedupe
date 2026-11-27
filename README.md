# PNEZ CSV Deduplicator

A small Python utility that removes duplicate survey points from PNEZ-format
CSV files. Drop files into `input/`, run the script, and deduplicated copies
appear in `output/` under the same filenames.

## File format

Comma-separated PNEZ(D) rows, no header:

```
Point,Northing,Easting,Elevation,Feature code
2001,1000.000,2000.000,100.000,GROUND
```

Other column orders (PENZD etc.) are supported via `--format`.

Rows that don't parse (short rows, headers, blank-adjacent junk) are passed
through to the output unchanged.

## Usage

```
uv run deduplicate.py [options]
```

(or `python deduplicate.py` — no dependencies outside the standard library)

| Option | Default | Meaning |
| --- | --- | --- |
| `-t`, `--tolerance <dist>` | `0` | Treat points within this horizontal distance (same units as the file) as the same location. `0` means exact coordinate match. |
| `-f`, `--format <order>` | `PNEZD` | Column order, a permutation of `PNEZD` (P=point, N=northing, E=easting, Z=elevation, D=feature code). A trailing `D` may be omitted, so `PENZ` works too. |
| `--per-code` | off | Keep one point per location *per feature code*, instead of flattening. |

### Examples

```
uv run deduplicate.py              # exact match, flatten feature codes
uv run deduplicate.py -t 0.001     # also merge points within 1 mm
uv run deduplicate.py -f PENZD     # easting-before-northing files
uv run deduplicate.py --per-code   # allow one point per code at a location
```

Each run prints a summary per file:

```
example-survey.csv: 42984 rows -> 13944 kept (29040 duplicates removed)
```

## How duplicates are decided

- The **first** occurrence of a point wins; later duplicates are dropped.
  Output preserves the original row order and formatting.
- Feature codes are compared **case-insensitively** (`GROUND` and `ground`
  are the same code). The first-seen casing is what gets written out.
- By default, duplicates are matched on location only (**flatten** mode). If
  genuinely different feature codes appear at one location, the kept row's
  code field becomes the codes joined with `/` (e.g. `GROUND/TOE`).
- With `--per-code`, the feature code is part of the identity, so one point
  per distinct code may survive at the same location.
- With a tolerance, points are matched to the nearest already-kept point
  within the tolerance (2D horizontal distance, elevation ignored) using a
  spatial-hash grid, so large files stay fast.

## Repo layout

```
deduplicate.py   the whole app
input/           source CSVs (contents gitignored)
output/          deduplicated CSVs (contents gitignored)
tests/           synthetic tests: uv run --with pytest python -m pytest
```

Survey data files are intentionally not committed.
