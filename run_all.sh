#!/usr/bin/env bash
# One-command reproduction of every table and figure in the paper.
set -e
echo "== [1/3] Downloading EUROCONTROL data (or verifying data/raw/) =="
python src/download_data.py
echo "== [2/3] Building panels under the five-rule protocol =="
python src/pipeline_divergence.py
echo "== [3/3] Reproducing paper quantifications =="
python src/audit_data_note.py
echo "Done. See output/ for figures and tables."
