# EUROCONTROL state-level CO2 statistics: layered robustness audit (v2.0)

Reproduction package for

> Yurtsever, Ö. *Processing errors, population definitions and analytic choices in public aviation CO2 statistics:
> a layered robustness audit of EUROCONTROL state-level data.* Manuscript under review.
> Istanbul Nişantaşı University, Civil Aviation School. ORCID 0009-0008-7359-2672.

Archived version (all versions): https://doi.org/10.5281/zenodo.21217148

## What it does

The paper separates three kinds of decisions between the published EUROCONTROL files and an estimate:

| Layer | Examples | Treatment |
|---|---|---|
| 1 Processing errors | wrong character decoding, positional binding of files, grouping by the shared ICAO codes LY/LS, comma splitting, treating partial 2026 as a year | corrected once; re-introduced only as stress tests |
| 2 Population | published vs national entities (Canary Islands), all entities vs commercial-aviation markets (Monaco, Liechtenstein), roster | declared before estimation; both populations reported |
| 3 Specification | temporal aggregation, territorial-regime treatment, OLS vs Huber, classical vs robust inference | 256-specification multiverse on corrected data |

## Run

```bash
pip install -r requirements.txt
bash run_all.sh          # or run the four commands inside it one by one
```

Outputs are written to `out/`: `results.json`, `multiverse_corrected.csv`, `stress_tests.csv`, `jackknife.csv`,
`annual_slopes.csv`, `crosswalk.csv`, Fig1–Fig6, and `ESM_1–3.xlsx`.

## Files

| File | Purpose |
|---|---|
| `analysis.py` | audit, stress tests, multiverse, ANOVA, influence, jackknife, panel, pre-pandemic comparison, emissions per departure, volatility, crosswalk |
| `figures.py` | Fig. 1–6 (174 mm, 600 dpi TIFF + PNG) |
| `build_esm.py` | Online Resources 1–3 |
| `tests/test_pipeline.py` | record counts, key uniqueness, shared codes, schema change, encoding trap, partial year, NOTE flags, headline results |
| `data/raw/` | the 17 input files (vintage 4 July 2026) and `SHA256SUMS.txt` |

## Licence

Code: MIT. Data in `data/raw/`: © EUROCONTROL, reproduced with attribution (see `data/README.md`).
