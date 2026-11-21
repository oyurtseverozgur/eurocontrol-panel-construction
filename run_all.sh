#!/usr/bin/env bash
# Reproduce every number, table and figure of the paper from data/raw/.
set -e
python analysis.py     # stops if data/raw/ differs from data/raw/SHA256SUMS.txt
python figures.py      # out/Fig1-Fig6 (TIFF 600 dpi + PNG)
python build_esm.py    # Online Resources 1-3 (ESM_1-3.xlsx)
pytest -q tests        # 10 transformation tests
