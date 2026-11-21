#!/usr/bin/env python3
"""Build Online Resources 1-3 (ESM_1-3.xlsx) from out/."""
import json, pandas as pd
from openpyxl import load_workbook
R = json.load(open("out/results.json"))
info = pd.DataFrame({"Field": ["Article", "Journal", "Author", "Affiliation", "Corresponding e-mail", "Content"],
 "Value": ["Processing errors, population definitions and analytic choices in public aviation CO2 statistics: a layered robustness audit of EUROCONTROL state-level data",
           "Environmental Monitoring and Assessment", "Özgür Yurtsever", "Civil Aviation School, Istanbul Nişantaşı University, Istanbul, Türkiye", "ozgur.yurtsever@nisantasi.edu.tr", ""]})
def write(path, content, sheets):
    i = info.copy(); i.loc[5, "Value"] = content
    with pd.ExcelWriter(path) as w:
        i.to_excel(w, sheet_name="Info", index=False)
        for n, df in sheets: df.to_excel(w, sheet_name=n, index=False)
    wb = load_workbook(path)
    for ws in wb:
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(70, max(10, max(len(str(c.value or "")) for c in col[:60])*0.95))
        ws.freeze_panes = "A2"
    wb.save(path)
h = pd.DataFrame([{"file": k, "sha256": v, "records": R["rows_per_file"][k[-8:-4]], "downloaded": "2026-07-04",
                   "source": "https://ansperformance.eu/reference/dataset/emissions/"} for k, v in R["hashes"].items()])
write("ESM_1.xlsx", "Online Resource 1: input vintage (SHA-256 hashes and record counts of the 17 EUROCONTROL files)", [("Vintage", h)])
write("ESM_2.xlsx", "Online Resource 2: versioned crosswalk from published entities to canonical identifiers (vintage 2026-07-04)", [("Crosswalk", pd.read_csv("out/crosswalk.csv"))])
lst = lambda v: str(v) if isinstance(v, list) else v
pn = pd.DataFrame([dict(population=k.split("|")[0], window=k.split("|")[1], **{a: lst(b) for a, b in v.items()}) for k, v in R["panel"].items()])
pre = pd.DataFrame([dict(key=k, **{a: lst(b) for a, b in v.items()}) for k, v in R["pre_pandemic"].items()])
I = R["intensity"]
it = pd.DataFrame([{"quantity": k, "value": lst(v) if not isinstance(v, dict) else str(v)} for k, v in I.items()])
write("ESM_3.xlsx", "Online Resource 3: all 256 corrected-data specifications, Layer-1 stress tests, ANOVA, jackknife, influence, panel regressions, pre-pandemic comparison, annual slopes, emissions per departure, sigma and volatility",
      [("Multiverse_256", pd.read_csv("out/multiverse_corrected.csv")), ("Stress_tests", pd.read_csv("out/stress_tests.csv")),
       ("ANOVA", pd.read_csv("out/multiverse_anova.csv").rename(columns={"Unnamed: 0": "term"})), ("Jackknife", pd.read_csv("out/jackknife.csv")),
       ("Influence", pd.read_csv("out/influence_all.csv").rename(columns={"Unnamed: 0": "entity", "UNIT": "entity"})), ("Panel", pn),
       ("Pre_pandemic", pre), ("Annual_slopes", pd.read_csv("out/annual_slopes.csv")), ("Per_departure", it),
       ("Sigma_annual", pd.read_csv("out/sigma_annual.csv")), ("Volatility", pd.read_csv("out/volatility.csv").rename(columns={"Unnamed: 0": "entity", "UNIT": "entity"}))])
print("ESM written")
