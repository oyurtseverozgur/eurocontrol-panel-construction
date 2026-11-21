#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Figures for the EMA manuscript (run after analysis_v2.py). 174 mm wide, 600 dpi TIFF."""
import glob, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import statsmodels.api as sm

OUT = "out"
BLUE, ORANGE, AQUA, YELLOW, RED, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e34948", "#4a3aa7"
GRAY, INK, MUTED = "#a3a29c", "#0b0b0b", "#52514e"
W = 174 / 25.4
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8, "axes.edgecolor": "#8c8b86",
    "axes.linewidth": 0.6, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "legend.fontsize": 7, "figure.dpi": 150, "savefig.dpi": 600,
    "axes.spines.top": False, "axes.spines.right": False})
R = json.load(open(f"{OUT}/results.json"))
raw = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("data/raw/co2_emmissions_by_state_*.csv"))], ignore_index=True)
raw["STATE_NAME"] = raw.STATE_NAME.astype(str).str.strip(); raw["TM"] = raw.YEAR*12 + raw.MONTH - 1; raw["CO2"] = raw["CO2_QTY_TONNES"]

def lab(ax, s): ax.text(-0.02, 1.04, s, transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right", va="bottom", color=INK)
def save(fig, name):
    fig.savefig(f"{OUT}/{name}.tiff", bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight", dpi=300); plt.close(fig)

# ---------- Fig 1: coverage and issue map
LAYER1 = {"SERBIA", "MONTENEGRO", "SWITZERLAND", "LIECHTENSTEIN", "TÜRKIYE", "MOLDOVA, REPUBLIC OF"}
DOC = {"UNITED KINGDOM", "CYPRUS", "NORWAY", "DENMARK", "PORTUGAL", "SPAIN", "CANARY ISLANDS", "FRANCE"}
def cls(s):
    if s in ("MONACO", "LIECHTENSTEIN"): return 3
    if s in ("LATVIA", "GEORGIA", "ESTONIA"): return 2
    if s in LAYER1: return 4
    if s in DOC: return 5
    return 1
order = sorted(raw.STATE_NAME.unique(), key=lambda s: (cls(s), s))
months = np.arange(raw.TM.min(), raw.TM.max()+1)
Mx = np.zeros((len(order), len(months)))
for i, s in enumerate(order):
    for t in raw.loc[raw.STATE_NAME == s, "TM"]: Mx[i, t-months[0]] = cls(s)
cmap = ListedColormap(["#ffffff", "#c9dcf3", YELLOW, ORANGE, RED, VIOLET])
fig, ax = plt.subplots(figsize=(W, 6.4))
ax.imshow(Mx, aspect="auto", cmap=cmap, vmin=0, vmax=5, interpolation="nearest")
nice = {"MOLDOVA, REPUBLIC OF": "Moldova, Republic of", "TÜRKIYE": "Türkiye", "UNITED KINGDOM": "United Kingdom",
        "BOSNIA AND HERZEGOVINA": "Bosnia and Herzegovina", "NORTH MACEDONIA": "North Macedonia", "CANARY ISLANDS": "Canary Islands"}
ax.set_yticks(range(len(order))); ax.set_yticklabels([nice.get(s, s.title()) for s in order], fontsize=6.2)
ax.set_xticks([(y*12)-months[0] for y in range(2010, 2027)]); ax.set_xticklabels([str(y) for y in range(2010, 2027)], rotation=90, fontsize=6.5)
ax.axvline(2019*12-months[0]-0.5, color=INK, lw=0.8, ls="--"); ax.grid(False)
ax.legend(handles=[Patch(fc="#c9dcf3", ec="#8c8b86", lw=.4, label="No issue identified"),
                   Patch(fc=YELLOW, label="Population: late entrant"), Patch(fc=ORANGE, label="Population: very-low-activity entity"),
                   Patch(fc=RED, label="Processing: shared code or name-encoding trap"),
                   Patch(fc=VIOLET, label="Population: documented territorial definition"),
                   Patch(fc="white", ec="#8c8b86", lw=.4, label="No record")],
          loc="upper center", bbox_to_anchor=(0.42, -0.07), ncol=3, fontsize=6.6)
save(fig, "Fig1")

# ---------- Fig 2: processing-error stress tests
mne = raw[raw.STATE_NAME == "MONTENEGRO"].set_index("TM").CO2; srb = raw[raw.STATE_NAME == "SERBIA"].set_index("TM").CO2
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 2.7), gridspec_kw={"width_ratios": [1.15, 1]})
t = mne.index.values/12
a1.plot(t, (mne+srb).values/1e3, color=RED, lw=1.1, label="Grouped by STATE_CODE (LY)")
a1.plot(t, mne.values/1e3, color=BLUE, lw=1.5, label="Montenegro, grouped by entity")
a1.set_ylabel("Monthly CO$_2$ (kt)"); a1.legend(loc="upper left"); a1.set_xlim(2010, 2026.4); a1.set_xticks(range(2010,2027,4)); lab(a1, "a")
st = pd.DataFrame(R["stress_tests"])
names = ["none (corrected)", "merge on STATE_CODE", "cp1252 decoding (Türkiye lost)", "naive comma split (Moldova lost)", "partial 2026 treated as annual"]
short = ["Corrected", "Merge on STATE_CODE", "cp1252 decoding", "Naive comma split", "Partial year as annual"]
y = np.arange(len(names))[::-1]
for scope, c, off, mk in [("all", ORANGE, 0.17, "D"), ("commercial", BLUE, -0.17, "o")]:
    s = st[st.scope == scope].set_index("error").loc[names]
    a2.scatter(s.beta, y+off, color=c, s=22, marker=mk, edgecolor="white", lw=.5, zorder=3,
               label="All reporting entities" if scope == "all" else "Commercial-aviation population")
a2.axvline(0, color=MUTED, lw=.8); a2.set_yticks(y); a2.set_yticklabels(short); a2.set_xticks([-0.012,-0.008,-0.004,0]); a2.set_xticklabels(["−0.012","−0.008","−0.004","0"])
a2.set_xlabel(r"$\hat\beta$, January 2019–2026 (OLS)"); a2.legend(loc="upper center", bbox_to_anchor=(0.45, -0.28), ncol=2, fontsize=6.5); a2.grid(axis="y", visible=False); lab(a2, "b")
fig.tight_layout(); save(fig, "Fig2")

# ---------- Fig 3: specification curves by population
mv = pd.read_csv(f"{OUT}/multiverse_corrected.csv").sort_values("beta").reset_index(drop=True)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 5.0), sharex=True, gridspec_kw={"height_ratios": [1.15, 1.35]})
x = np.arange(len(mv)); col = np.where(mv.scope == "all", ORANGE, BLUE)
a1.vlines(x, mv.ci_lo, mv.ci_hi, color=col, lw=0.6, alpha=0.45)
a1.scatter(x, mv.beta, c=col, s=7, zorder=3, edgecolor="none")
a1.axhline(0, color=MUTED, lw=0.8); a1.set_ylabel(r"$\hat\beta$ (95% CI)")
a1.legend(handles=[Line2D([], [], color=ORANGE, marker="o", lw=0, label="All reporting entities"),
                   Line2D([], [], color=BLUE, marker="o", lw=0, label="Commercial-aviation population")], loc="upper left", ncol=2)
lab(a1, "a")
rows = [("entity", "published", "Published entities"), ("entity", "national", "Canary Is. merged"),
        ("roster", "balanced", "Balanced roster"), ("roster", "unbalanced", "With late entrants"),
        ("agg", "jan", "January"), ("agg", "janmay", "Jan–May"), ("agg", "ttm", "Trailing 12 months"), ("agg", "annual", "Calendar year"),
        ("regime", "none", "No territorial control"), ("regime", "note", "NOTE indicator"), ("regime", "doc", "Documented-aggregation indicator"),
        ("regime", "exclude", "Aggregated entities excluded"), ("estimator", "ols", "OLS"), ("estimator", "huber", "Huber M")]
for i, (c, v, l) in enumerate(rows):
    m = (mv[c] == v).values
    a2.scatter(x[m], np.full(m.sum(), i), c=col[m], s=4, marker="|", lw=0.9)
a2.set_yticks(range(len(rows))); a2.set_yticklabels([r[2] for r in rows], fontsize=6.6)
a2.invert_yaxis(); a2.set_xlabel("Specification rank (256 corrected-data specifications)"); a2.grid(False)
for b in [1.5, 3.5, 7.5, 11.5]: a2.axhline(b, color="#e4e3df", lw=0.6)
lab(a2, "b"); fig.tight_layout(); save(fig, "Fig3")

# ---------- Fig 4: influence and sigma trajectories
inf = pd.read_csv(f"{OUT}/influence_all.csv", index_col=0); sg = pd.read_csv(f"{OUT}/sigma_annual.csv", index_col=0)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 2.8))
isM = inf.index == "MONACO"
a1.scatter(inf.lnE2019[~isM], 100*inf.growth[~isM], s=14, color=BLUE, edgecolor="white", lw=.4, label="Commercial-aviation population (39)")
a1.scatter(inf.lnE2019[isM], 100*inf.growth[isM], s=30, color=ORANGE, edgecolor="white", lw=.4, marker="D", label="Monaco")
xx = np.linspace(inf.lnE2019.min(), inf.lnE2019.max(), 50)
for sub, c, ls, l in [(inf, ORANGE, "--", "Fit, all reporting entities"), (inf[~isM], BLUE, "-", "Fit, commercial population")]:
    m = sm.OLS(100*sub.growth, sm.add_constant(sub.lnE2019)).fit(); a1.plot(xx, m.params.iloc[0]+m.params.iloc[1]*xx, color=c, ls=ls, lw=1.2, label=l)
a1.set_xlabel("ln January CO$_2$ 2019 (t)"); a1.set_ylabel("Annualised growth 2019–2026 (% yr$^{-1}$)")
a1.legend(loc="lower left", bbox_to_anchor=(0.12, 0), fontsize=6.2); lab(a1, "a")
a2.plot(sg.index, sg["all"], color=ORANGE, lw=1.5, marker="D", ms=3, label="All reporting entities")
a2.plot(sg.index, sg["commercial"], color=BLUE, lw=1.5, marker="o", ms=3, label="Commercial-aviation population")
a2.set_xticks(range(2010,2026,3)); a2.set_xlabel("Year"); a2.set_ylabel("SD of ln annual CO$_2$ (σ)"); a2.legend(loc="center right", fontsize=6.5); lab(a2, "b")
fig.tight_layout(); save(fig, "Fig4")

# ---------- Fig 5: timing of the differential
pa = pd.read_csv(f"{OUT}/annual_slopes.csv"); PR = R["pre_pandemic"]
ref = {r["scope"]: r for r in R["multiverse"]["reference_specs"] if r["agg"] == "jan"}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 2.7), gridspec_kw={"width_ratios": [1.6, 1]})
a1.axvspan(2019.5, 2021.5, color="#f1efe8", zorder=0)
for scope, c, off, mk in [("all", ORANGE, -0.15, "D"), ("commercial", BLUE, 0.15, "o")]:
    g = pa[pa.scope == scope]
    a1.vlines(g.year+off, g.lo, g.hi, color=c, lw=0.9, alpha=0.6)
    a1.scatter(g.year+off, g.beta, color=c, s=14, marker=mk, zorder=3, edgecolor="white", lw=.4,
               label="All reporting entities" if scope == "all" else "Commercial-aviation population")
a1.axhline(0, color=MUTED, lw=.8); a1.set_xticks(range(2011, 2026, 2)); a1.set_xlabel("Year of annual growth")
a1.set_ylabel(r"Slope of growth on lagged ln CO$_2$"); a1.set_ylim(-0.13, 0.10); a1.legend(loc="lower left", fontsize=6.4); lab(a1, "a")
a1.text(2020.5, 0.088, "pandemic", ha="center", fontsize=6.5, color=MUTED)
rows = [("commercial", "2012–2019", PR["commercial|jan|2012-2019"]), ("commercial", "2019–2026", None),
        ("all", "2012–2019", PR["all|jan|2012-2019"]), ("all", "2019–2026", None)]
ylab = []
for i, (scope, w, r) in enumerate(rows):
    yy = len(rows) - 1 - i
    if r is None:
        rr = ref[scope]; b, lo, hi = rr["beta"], rr["beta"]-1.96*rr["se_classical"], rr["beta"]+1.96*rr["se_classical"]
    else:
        b, lo, hi = r["beta"], r["ci"][0], r["ci"][1]
    c = BLUE if scope == "commercial" else ORANGE
    a2.plot([lo, hi], [yy, yy], color=c, lw=2, solid_capstyle="round"); a2.plot(b, yy, "o" if w.startswith("2019") else "s", color=c, ms=6, mec="white")
    ylab.append(("Commercial" if scope == "commercial" else "All entities") + ", " + w)
a2.axvline(0, color=MUTED, lw=.8); a2.set_yticks(range(len(rows))[::-1]); a2.set_yticklabels(ylab, fontsize=6.8)
a2.set_xticks([-0.015, -0.010, -0.005, 0, 0.005]); a2.set_xticklabels(["−0.015", "−0.010", "−0.005", "0", "0.005"])
a2.set_xlabel(r"$\hat\beta$, January endpoints (95% CI)"); a2.grid(axis="y", visible=False); lab(a2, "b")
fig.tight_layout(); save(fig, "Fig5")

# ---------- Fig 6: volatility, matched periods
v = pd.read_csv(f"{OUT}/volatility.csv", index_col=0)
fig, axs = plt.subplots(1, 2, figsize=(W, 2.6), sharey=False)
for ax, col_, key, letter in [(axs[0], "vol_monthly_2011_2019", "monthly_2011_2019", "a"), (axs[1], "vol_january_2011_2019", "january_2011_2019", "b")]:
    ax.scatter(v.size_ln2010, v[col_], s=14, color=BLUE, edgecolor="white", lw=.4)
    m = sm.OLS(v[col_], sm.add_constant(v.size_ln2010)).fit(); xx = np.linspace(v.size_ln2010.min(), v.size_ln2010.max(), 50)
    ax.plot(xx, m.params.iloc[0]+m.params.iloc[1]*xx, color=ORANGE, lw=1.2)
    rr = R["volatility"][key]
    ax.text(0.97, 0.95, f"slope = {rr['slope']:.4f}\n95% CI [{rr['ci'][0]:.4f}, {rr['ci'][1]:.4f}]", transform=ax.transAxes, ha="right", va="top", fontsize=6.8)
    ax.set_xlabel("ln mean monthly CO$_2$ 2010 (t)"); lab(ax, letter)
axs[0].set_ylabel("SD of monthly year-on-year log change"); axs[1].set_ylabel("SD of January-to-January log change")
fig.tight_layout(); save(fig, "Fig6")
print("figures done")
