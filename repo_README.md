# EUROCONTROL Panel Construction — Companion Repository

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](requirements.txt)

Reproducibility package for:

> **Yurtsever, Ö.** *Small-State Aviation Carbon Dynamics: Data Quality, Code Collisions, and
> Panel Construction in EUROCONTROL Emission Statistics.* (under review)
> Istanbul Nişantaşı University, Civil Aviation School. ORCID: 0009-0008-7359-2672.

This repository contains the data download script, cleaning routines, the audit code that
reproduces **every table and figure** in the paper, and the recommended five-rule panel
construction protocol for the EUROCONTROL state-level CO₂ emission statistics (2010–2026).

---

## Why this repository exists

The EUROCONTROL Small Emitters Tool (SET) state-level CO₂ files are excellent public data,
but the construction steps between the raw files and an estimation panel are not innocuous.
The paper documents five concrete hazards:

| # | Hazard | Affected | Consequence if ignored |
|---|--------|----------|------------------------|
| 1 | `STATE_CODE` collision **LY** | Serbia, Montenegro | Montenegro inflated by **+679 %** on average |
| 2 | `STATE_CODE` collision **LS** | Switzerland, Liechtenstein | Liechtenstein inflated **×740,000** |
| 3 | Late entrants | Latvia (2011), Georgia (2014), Estonia (2018) | phantom growth; shifting roster |
| 4 | Microstates | Monaco, Liechtenstein | log-scale leverage: flips β-convergence from *p* = 0.009 to *p* = 0.38 |
| 5 | Estimation flags & name encoding | DK, NO, PT, UK; Türkiye, Moldova | silent comparability caveats; silent row loss |

**Headline result** (Table 3 of the paper): four defensible-looking panel constructions,
applied to identical raw data, disagree on whether the dataset's central distributional
finding (β-convergence, 2019–2026) exists at all.

## Repository structure

```
eurocontrol-panel-construction/
├── README.md                  ← you are here
├── LICENSE                    ← MIT (code); data remains © EUROCONTROL
├── CITATION.cff               ← citation metadata (GitHub "Cite this repository")
├── .zenodo.json               ← Zenodo deposit metadata
├── requirements.txt           ← pinned Python dependencies
├── run_all.sh                 ← one-command full reproduction
├── src/
│   ├── download_data.py       ← fetches the EUROCONTROL SET dataset
│   ├── pipeline_divergence.py ← panel construction pipeline (five-rule protocol)
│   └── audit_data_note.py     ← reproduces every quantification in the paper
├── data/
│   ├── README.md              ← data provenance and licence notes
│   ├── raw/                   ← EUROCONTROL CSVs (populated by download_data.py)
│   └── derived/
│       └── jan_panel.csv      ← name-keyed January panel, 2010–2026 (derived)
└── output/                    ← figures (300 DPI) and tables (CSV), written by the scripts
```

## Quickstart

```bash
git clone https://github.com/[username]/eurocontrol-panel-construction.git
cd eurocontrol-panel-construction
pip install -r requirements.txt

# 1) Obtain the raw data (or place the yearly CSVs in data/raw/ manually)
python src/download_data.py

# 2) Build the panels under the five-rule protocol (writes output/)
python src/pipeline_divergence.py

# 3) Reproduce every number in the paper (Tables 1–3, Figures 1–3)
python src/audit_data_note.py
```

Or simply:

```bash
bash run_all.sh
```

Google Colab users: upload the repository, `pip install -r requirements.txt`, and run the
same three scripts; no other configuration is required.

## The five-rule construction protocol

1. **Key on normalised state names, never on codes** — assert key uniqueness on load so
   collisions fail loudly.
2. **Normalise Unicode and parse quoted commas** — verify row counts against the source.
3. **Declare the roster** — report entry years; estimate on the balanced core; rerun on the
   unbalanced panel as robustness, not as default.
4. **Exclude microstates from log-scale/distributional statistics, and say so** — the
   exclusion is a modelling decision (33 % effect on dispersion), not housekeeping.
5. **Carry the estimation flag through** — report its incidence and include it as a binary
   control in regression specifications.

## Data provenance

Raw data: EUROCONTROL Aviation Intelligence Unit, *CO₂ emissions by State* (SET),
monthly, January 2010 onwards. Documentation:
<https://ansperformance.eu/reference/dataset/emissions/> — © EUROCONTROL, publicly
available. This repository redistributes only a small **derived** January extract
(`data/derived/jan_panel.csv`) for immediate reproducibility, with full attribution;
the complete raw files should be obtained from the source (see `data/README.md`).

## Citing

If you use this code or the construction protocol, please cite the paper (reference above)
and the archived software:

```bibtex
@software{yurtsever_eurocontrol_panel_2026,
  author    = {Yurtsever, {\"O}zg{\"u}r},
  title     = {EUROCONTROL Panel Construction: audit code and five-rule protocol},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.XXXXXXX},
  url       = {https://github.com/[username]/eurocontrol-panel-construction}
}
```

GitHub's "Cite this repository" button is powered by [`CITATION.cff`](CITATION.cff).

## Licence

Code: [MIT](LICENSE). The EUROCONTROL data remain the property of EUROCONTROL and are
subject to the source's terms of use.

---

### Maintainer notes — archiving on Zenodo (delete this section after release)

1. Create the GitHub repository and push all files (`git init && git add -A && git commit -m "v1.0.0" && git push`).
2. Log in to <https://zenodo.org> with the GitHub account → *GitHub* tab → flip the switch
   for `eurocontrol-panel-construction`.
3. On GitHub: *Releases → Draft a new release* → tag `v1.0.0` → publish. Zenodo archives it
   automatically and mints a DOI (metadata is read from `.zenodo.json`).
4. Replace every `10.5281/zenodo.XXXXXXX` and `[username]` in this README, in
   `CITATION.cff`, and in the manuscript's *Data and code availability* section with the
   minted DOI and your GitHub username.
