#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Separating processing errors, population definitions and analytic specifications
in EUROCONTROL state-level aviation CO2 statistics (2010-01 to 2026-05).

Reproduces every number, table and figure of the manuscript submitted to
Environmental Monitoring and Assessment.
Author : Ozgur Yurtsever, Istanbul Nisantasi University (ORCID 0009-0008-7359-2672)
Input  : data/co2_emmissions_by_state_YYYY.csv  (vintage downloaded 4 July 2026;
         SHA-256 hashes are checked against data/SHA256SUMS.txt)
Output : out/  (results.json, CSV tables)
"""
import glob, hashlib, itertools, json, os, sys
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

DATA, OUT = "data/raw", "out"
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(20260704)
R = {}

# ---------------------------------------------------------------- 0. vintage
files = sorted(glob.glob(f"{DATA}/co2_emmissions_by_state_*.csv"))
hashes = {os.path.basename(f): hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files}
ref = f"{DATA}/SHA256SUMS.txt"
if os.path.exists(ref):
    expected = dict(l.split()[::-1] for l in open(ref) if l.strip())
    bad = [k for k, v in hashes.items() if expected.get(k) != v]
    if bad:
        sys.exit(f"Input vintage differs from the archived snapshot: {bad}")
R["hashes"] = hashes

# ---------------------------------------------------------------- 1. correct load
frames, schema = [], {}
for f in files:
    d = pd.read_csv(f, encoding="utf-8")            # explicit decoding
    schema[int(f[-8:-4])] = list(d.columns)
    frames.append(d)
raw = pd.concat(frames, ignore_index=True)          # bind by column name
raw["STATE_NAME"] = raw["STATE_NAME"].astype(str).str.strip()
raw["FLAG"] = raw["NOTE"].astype(str).str.upper().eq("TRUE").astype(int)
raw["CO2"] = raw["CO2_QTY_TONNES"].astype(float)
raw["TM"] = raw["YEAR"] * 12 + raw["MONTH"] - 1
assert not raw.duplicated(["YEAR", "MONTH", "STATE_NAME"]).any()
R["n_rows"], R["n_entities"], R["n_months"] = len(raw), raw.STATE_NAME.nunique(), raw.TM.nunique()
R["rows_per_file"] = {int(f[-8:-4]): len(d) for f, d in zip(files, frames)}

# documented special territorial aggregations (EUROCONTROL dataset documentation)
DOC_AGG = {"UNITED KINGDOM", "CYPRUS", "NORWAY", "DENMARK", "PORTUGAL"}
NOTE_STATES = sorted(raw.loc[raw.FLAG == 1, "STATE_NAME"].unique())
R["note_states"] = NOTE_STATES
R["doc_agg_not_flagged"] = sorted(DOC_AGG - set(NOTE_STATES))
ENTRANTS = {"LATVIA", "GEORGIA", "ESTONIA"}
NONCOMM = {"MONACO", "LIECHTENSTEIN"}   # no aerodrome for fixed-wing commercial air transport

# ---------------------------------------------------------------- 2. layer 1: processing errors
E = {}
E["schema_change_year"] = min(y for y, c in schema.items() if "FLIGHT_MONTH" in c)
E["rows_new_schema"] = int(sum(len(d) for y, d in zip(schema, frames) if "FLIGHT_MONTH" in schema[y]))
E["rows_new_schema_share"] = E["rows_new_schema"] / len(raw)

def pooled_inflation(big, small):
    pv = raw[raw.STATE_NAME.isin([big, small])].pivot_table(index="TM", columns="STATE_NAME", values="CO2").dropna()
    tot = pv.sum(axis=1)
    out = {}
    for s in (big, small):
        r = tot / pv[s]
        out[s] = dict(months=len(pv), mean_pct=100*(r.mean()-1), min_pct=100*(r.min()-1),
                      max_pct=100*(r.max()-1), true_min=float(pv[s].min()), true_max=float(pv[s].max()))
    return out
E["LY"] = pooled_inflation("SERBIA", "MONTENEGRO")
E["LS"] = pooled_inflation("SWITZERLAND", "LIECHTENSTEIN")

bad = pd.concat([pd.read_csv(f, encoding="cp1252") for f in files], ignore_index=True)
bad["STATE_NAME"] = bad.STATE_NAME.astype(str).str.strip()
miss = bad[~bad.STATE_NAME.isin(set(raw.STATE_NAME))]
E["cp1252_unmatched_names"] = sorted(miss.STATE_NAME.unique())
E["cp1252_unmatched_rows"] = len(miss)
y25 = raw[raw.YEAR == 2025]
E["tur_share_2025"] = y25.loc[y25.STATE_NAME == "TÜRKIYE", "CO2"].sum() / y25.CO2.sum()
line = [l for l in open(files[0], encoding="utf-8") if "MOLDOVA" in l][0].strip()
E["moldova_naive_fields"], E["expected_fields"] = len(line.split(",")), len(schema[2010])
E["moldova_rows"] = int(raw.STATE_NAME.str.startswith("MOLDOVA").sum())
yl = raw.groupby("YEAR").agg(CO2=("CO2", "sum"), months=("MONTH", "nunique"))
E["final_year_months"] = int(yl.months.iloc[-1])
E["naive_annual_change"] = 100*(yl.CO2.iloc[-1]/yl.CO2.iloc[-2]-1)
jm = raw[raw.MONTH <= E["final_year_months"]].groupby("YEAR").CO2.sum()
E["like_for_like_change"] = 100*(jm.iloc[-1]/jm.iloc[-2]-1)
R["errors"] = E

# ---------------------------------------------------------------- 3. population descriptors
act = raw[raw.YEAR.between(2010, 2025)].groupby(["STATE_NAME", "YEAR"]).TF.sum().unstack() / 365
R["dep_per_day_2019"] = act[2019].sort_values().head(4).round(1).to_dict()
R["min_dep_per_day_any_year"] = act.drop(index=list(NONCOMM), errors="ignore").min(axis=1).min()
R["min_dep_state"] = act.drop(index=list(NONCOMM), errors="ignore").min(axis=1).idxmin()
R["monaco_monthly"] = raw[raw.STATE_NAME == "MONACO"].agg({"CO2": ["min", "max"], "TF": ["min", "max"]}).to_dict()
R["liechtenstein_months"] = int((raw.STATE_NAME == "LIECHTENSTEIN").sum())
first = raw.sort_values("TM").groupby("STATE_NAME").first()
R["entry"] = {s: f"{int(first.loc[s, 'YEAR'])}-{int(first.loc[s, 'MONTH']):02d}" for s in sorted(ENTRANTS)}
can = raw[raw.STATE_NAME == "CANARY ISLANDS"]; esp = raw[raw.STATE_NAME == "SPAIN"]
R["canary_share_of_spain_total_2025"] = can[can.YEAR == 2025].CO2.sum() / (can[can.YEAR == 2025].CO2.sum() + esp[esp.YEAR == 2025].CO2.sum())

# ---------------------------------------------------------------- 4. panel construction
def entities(d, entity):
    """entity='published' keeps reporting entities; 'national' merges Canary Islands into Spain."""
    d = d.copy()
    if entity == "national":
        d.loc[d.STATE_NAME == "CANARY ISLANDS", "STATE_NAME"] = "SPAIN"
        d = d.groupby(["YEAR", "MONTH", "TM", "STATE_NAME", "STATE_CODE"], as_index=False).agg(
            CO2=("CO2", "sum"), TF=("TF", "sum"), FLAG=("FLAG", "max"))
    d["UNIT"] = d["STATE_NAME"]
    return d

def code_keyed(d):
    d = d.copy(); d["UNIT"] = d["STATE_CODE"]
    names = d.groupby("STATE_CODE").STATE_NAME.agg(lambda s: "/".join(sorted(s.unique())))
    d = d.groupby(["YEAR", "MONTH", "TM", "UNIT"], as_index=False).agg(CO2=("CO2", "sum"), TF=("TF", "sum"), FLAG=("FLAG", "max"))
    d["STATE_NAME"] = d.UNIT.map(names)
    return d

def select(d, scope, roster, regime):
    drop = set()
    if scope == "commercial": drop |= NONCOMM
    if roster == "balanced": drop |= ENTRANTS | {"LIECHTENSTEIN"}
    if regime == "exclude": drop |= DOC_AGG
    keep = ~d.STATE_NAME.apply(lambda s: all(p in drop for p in s.split("/")))
    return d[keep]

def endpoints(d, agg, y0=2019, y1=2026):
    if agg == "jan":
        s = d[d.MONTH == 1]; a = s[s.YEAR == y0].groupby("UNIT").CO2.sum(); b = s[s.YEAR == y1].groupby("UNIT").CO2.sum(); T = y1-y0
    elif agg == "janmay":
        s = d[d.MONTH <= 5]; a = s[s.YEAR == y0].groupby("UNIT").CO2.sum(); b = s[s.YEAR == y1].groupby("UNIT").CO2.sum(); T = y1-y0
    elif agg == "ttm":
        t1, t0 = y1*12+4, y0*12+4
        a = d[(d.TM > t0-12) & (d.TM <= t0)].groupby("UNIT").CO2.sum(); b = d[(d.TM > t1-12) & (d.TM <= t1)].groupby("UNIT").CO2.sum(); T = (t1-t0)/12
    elif agg == "annual":
        a = d[d.YEAR == y0].groupby("UNIT").CO2.sum(); b = d[d.YEAR == 2025].groupby("UNIT").CO2.sum(); T = 2025-y0
    elif agg == "annual_partial":   # deliberate error: partial 2026 treated as a year
        a = d[d.YEAR == y0].groupby("UNIT").CO2.sum(); b = d[d.YEAR == 2026].groupby("UNIT").CO2.sum(); T = 2026-y0
    idx = a.index.intersection(b.index); a, b = a[idx], b[idx]
    ok = (a > 0) & (b > 0)
    return a[ok], b[ok], T

def fit_beta(d, agg, regime="none", est="ols"):
    a, b, T = endpoints(d, agg)
    x = np.log(a); g = (np.log(b) - np.log(a)) / T
    X = pd.DataFrame({"const": 1.0, "lnE0": x})
    if regime == "note":
        X["regime"] = d.groupby("UNIT").FLAG.max().reindex(x.index).fillna(0).astype(float)
    elif regime == "doc":
        X["regime"] = pd.Series([float(any(p in DOC_AGG for p in str(u).split("/"))) for u in x.index], index=x.index)
    out = dict(n=len(x), T=T)
    if est == "ols":
        m = sm.OLS(g, X).fit(); mh = sm.OLS(g, X).fit(cov_type="HC3")
        out.update(beta=m.params["lnE0"], se_classical=m.bse["lnE0"], p_classical=m.pvalues["lnE0"],
                   se_robust=mh.bse["lnE0"], p_robust=mh.pvalues["lnE0"])
    else:
        m = sm.RLM(g, X, M=sm.robust.norms.HuberT()).fit()
        mh = sm.RLM(g, X, M=sm.robust.norms.HuberT()).fit(cov="H2")
        out.update(beta=m.params["lnE0"], se_classical=m.bse["lnE0"], p_classical=m.pvalues["lnE0"],
                   se_robust=mh.bse["lnE0"], p_robust=mh.pvalues["lnE0"])
    out["lambda"] = -np.log(1 + out["beta"]*T) / T
    out["halflife"] = np.log(2) / out["lambda"] if out["lambda"] > 0 else np.inf
    return out

def sigma_end(d, agg):
    _, b, _ = endpoints(d, agg)
    return float(np.std(np.log(b), ddof=1))

PUB, NAT = entities(raw, "published"), entities(raw, "national")

# ---------------------------------------------------------------- 5. layers 2-3: multiverse on corrected data
grid = list(itertools.product(["published", "national"], ["all", "commercial"], ["balanced", "unbalanced"],
                              ["jan", "janmay", "ttm", "annual"], ["none", "note", "doc", "exclude"], ["ols", "huber"]))
rows = []
for ent, scope, ros, agg, reg, est in grid:
    d = select(PUB if ent == "published" else NAT, scope, ros, reg)
    r = fit_beta(d, agg, reg if reg in ("note", "doc") else "none", est)
    rows.append(dict(entity=ent, scope=scope, roster=ros, agg=agg, regime=reg, estimator=est, sigma_end=sigma_end(d, agg), **r))
mv = pd.DataFrame(rows)
mv["ci_lo"] = mv.beta - 1.96*mv.se_classical; mv["ci_hi"] = mv.beta + 1.96*mv.se_classical
mv["sig_classical"] = mv.p_classical < 0.05; mv["sig_robust"] = mv.p_robust < 0.05
mv.to_csv(f"{OUT}/multiverse_corrected.csv", index=False)
M = {}
M["n_specs"] = len(mv)
M["all_negative"] = bool((mv.beta < 0).all())
M["beta_range"] = [float(mv.beta.min()), float(mv.beta.max())]
M["by_scope"] = {s: dict(n=int(len(g)), beta_median=float(g.beta.median()), beta_min=float(g.beta.min()),
                         beta_max=float(g.beta.max()), lambda_median=float(g["lambda"].median()),
                         halflife_median=float(g.halflife.median()),
                         sig_classical=float(g.sig_classical.mean()), sig_robust=float(g.sig_robust.mean()),
                         sigma_end_min=float(g.sigma_end.min()), sigma_end_max=float(g.sigma_end.max()))
                 for s, g in mv.groupby("scope")}
fit = smf.ols("beta ~ C(entity)+C(scope)+C(roster)+C(agg)+C(regime)+C(estimator)", data=mv).fit()
an = sm.stats.anova_lm(fit, typ=2); an["eta2"] = an.sum_sq / an.sum_sq.sum()
an.to_csv(f"{OUT}/multiverse_anova.csv")
M["eta2"] = {k.replace("C(", "").replace(")", ""): float(v) for k, v in an.eta2.items()}
# within-scope decomposition
M["eta2_within_scope"] = {}
for s, g in mv.groupby("scope"):
    f2 = smf.ols("beta ~ C(entity)+C(roster)+C(agg)+C(regime)+C(estimator)", data=g).fit()
    a2 = sm.stats.anova_lm(f2, typ=2); a2["eta2"] = a2.sum_sq / a2.sum_sq.sum()
    M["eta2_within_scope"][s] = {k.replace("C(", "").replace(")", ""): float(v) for k, v in a2.eta2.items()}
M["sig_by_scope_estimator"] = {f"{a}|{b}": dict(classical=float(g.sig_classical.mean()), robust=float(g.sig_robust.mean()))
                               for (a, b), g in mv.groupby(["scope", "estimator"])}
M["median_beta_by"] = {c: {k: float(v) for k, v in mv.groupby(c).beta.median().items()}
                       for c in ["entity", "scope", "roster", "agg", "regime", "estimator"]}
ref_spec = mv[(mv.entity == "published") & (mv.roster == "balanced") & (mv.regime == "none") & (mv.estimator == "ols")]
M["reference_specs"] = ref_spec.set_index(["scope", "agg"])[["beta", "se_classical", "p_classical", "se_robust", "p_robust", "lambda", "halflife", "n"]].round(5).reset_index().to_dict("records")
R["multiverse"] = M

# ---------------------------------------------------------------- 6. layer-1 stress tests on the estimand
base = dict(agg="jan")
st = []
for scope in ["all", "commercial"]:
    dref = select(PUB, scope, "balanced", "none")
    r0 = fit_beta(dref, "jan")
    st.append(dict(scope=scope, error="none (corrected)", **{k: r0[k] for k in ("beta", "p_classical", "n")}))
    dc = select(code_keyed(raw), scope, "balanced", "none")
    r = fit_beta(dc, "jan"); st.append(dict(scope=scope, error="merge on STATE_CODE", **{k: r[k] for k in ("beta", "p_classical", "n")}))
    r = fit_beta(dref[dref.STATE_NAME != "TÜRKIYE"], "jan"); st.append(dict(scope=scope, error="cp1252 decoding (Türkiye lost)", **{k: r[k] for k in ("beta", "p_classical", "n")}))
    r = fit_beta(dref[~dref.STATE_NAME.str.startswith("MOLDOVA")], "jan"); st.append(dict(scope=scope, error="naive comma split (Moldova lost)", **{k: r[k] for k in ("beta", "p_classical", "n")}))
    r = fit_beta(dref, "annual_partial"); st.append(dict(scope=scope, error="partial 2026 treated as annual", **{k: r[k] for k in ("beta", "p_classical", "n")}))
st = pd.DataFrame(st); st.to_csv(f"{OUT}/stress_tests.csv", index=False)
R["stress_tests"] = st.to_dict("records")

# ---------------------------------------------------------------- 7. influence & jackknife
dall = select(PUB, "all", "balanced", "none")
a, b, T = endpoints(dall, "jan"); x = np.log(a); g = (np.log(b)-np.log(a))/T
m = sm.OLS(g, sm.add_constant(x)).fit(); inf = m.get_influence()
cd = pd.Series(inf.cooks_distance[0], index=x.index); lev = pd.Series(inf.hat_matrix_diag, index=x.index)
stud = pd.Series(inf.resid_studentized_external, index=x.index)
R["influence"] = dict(monaco_cooks=float(cd["MONACO"]), monaco_leverage=float(lev["MONACO"]), monaco_stud=float(stud["MONACO"]),
                      next_cooks=float(cd.drop("MONACO").max()), next_state=cd.drop("MONACO").idxmax(), threshold=4/len(x),
                      monaco_growth=float(g["MONACO"]), monaco_ln2019=float(x["MONACO"]), mean_ln2019_others=float(x.drop("MONACO").mean()))
pd.DataFrame({"cooks": cd, "leverage": lev, "stud_resid": stud, "lnE2019": x, "growth": g}).to_csv(f"{OUT}/influence_all.csv")
jk = []
for scope in ["all", "commercial"]:
    dd = select(PUB, scope, "balanced", "none"); a_, b_, _ = endpoints(dd, "jan")
    for u in a_.index:
        r = fit_beta(dd[dd.UNIT != u], "jan"); jk.append(dict(scope=scope, dropped=u, beta=r["beta"], p=r["p_classical"]))
jk = pd.DataFrame(jk); jk.to_csv(f"{OUT}/jackknife.csv", index=False)
R["jackknife"] = {s: dict(n=int(len(g)), beta_min=float(g.beta.min()), beta_max=float(g.beta.max()),
                          n_sig=int((g.p < 0.05).sum()), sig_drops=list(g[g.p < 0.05].dropped)[:5])
                  for s, g in jk.groupby("scope")}

# ---------------------------------------------------------------- 8. panel robustness (annual, year FE, clustered SE)
ann = PUB[PUB.YEAR.between(2010, 2025)].groupby(["UNIT", "YEAR"]).CO2.sum().reset_index()
ann = ann.sort_values(["UNIT", "YEAR"]); ann["lnE"] = np.log(ann.CO2)
ann["lag"] = ann.groupby("UNIT").lnE.shift(1); ann["lagyear"] = ann.groupby("UNIT").YEAR.shift(1)
ann = ann[(ann.YEAR - ann.lagyear) == 1].copy(); ann["g"] = ann.lnE - ann.lag
P = {}
for scope in ["all", "commercial"]:
    keep = set(select(PUB, scope, "balanced", "none").UNIT.unique())
    for w, (y0, y1) in {"2011-2019": (2011, 2019), "2020-2025": (2020, 2025), "2022-2025": (2022, 2025)}.items():
        dd = ann[ann.UNIT.isin(keep) & ann.YEAR.between(y0, y1)]
        mm = smf.ols("g ~ lag + C(YEAR)", data=dd).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dd.UNIT)[0]})
        P[f"{scope}|{w}"] = dict(beta=float(mm.params["lag"]), se=float(mm.bse["lag"]), p=float(mm.pvalues["lag"]),
                                 ci=[float(v) for v in mm.conf_int().loc["lag"]], n_obs=int(mm.nobs), n_units=int(dd.UNIT.nunique()))
R["panel"] = P

# ---- 8b. does the differential predate the pandemic? (same 7-year horizon, pre-pandemic endpoints)
def cross(d, y0, y1, agg, value="CO2"):
    if agg == "jan":   s = d[d.MONTH == 1]
    elif agg == "janmay": s = d[d.MONTH <= 5]
    else: s = d
    a = s[s.YEAR == y0].groupby("UNIT")[value].sum(); b = s[s.YEAR == y1].groupby("UNIT")[value].sum()
    idx = a.index.intersection(b.index); a, b = a[idx], b[idx]
    return np.log(a), (np.log(b) - np.log(a)) / (y1 - y0)
PRE = {}
for scope in ["all", "commercial"]:
    dd = select(PUB, scope, "balanced", "none")
    for agg, (y0, y1) in {"jan": (2012, 2019), "janmay": (2012, 2019), "annual": (2012, 2019)}.items():
        x, g = cross(dd, y0, y1, agg); m = sm.OLS(g, sm.add_constant(x)).fit()
        PRE[f"{scope}|{agg}|{y0}-{y1}"] = dict(beta=float(m.params.iloc[1]), se=float(m.bse.iloc[1]), p=float(m.pvalues.iloc[1]),
                                              ci=[float(v) for v in m.conf_int().iloc[1]], n=int(len(x)))
    # pooled test: are the 2012-2019 and 2019-2026 January slopes different?
    x0, g0 = cross(dd, 2012, 2019, "jan"); x1, g1 = cross(dd, 2019, 2026, "jan")
    st_ = pd.concat([pd.DataFrame({"x": x0, "g": g0, "post": 0, "u": x0.index}), pd.DataFrame({"x": x1, "g": g1, "post": 1, "u": x1.index})])
    mm = smf.ols("g ~ x*post", data=st_).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(st_.u)[0]})
    PRE[f"{scope}|difference"] = dict(beta=float(mm.params["x:post"]), se=float(mm.bse["x:post"]), p=float(mm.pvalues["x:post"]),
                                      ci=[float(v) for v in mm.conf_int().loc["x:post"]])
R["pre_pandemic"] = PRE
# year-by-year cross-sectional slopes of annual growth on lagged log emissions
path = []
for scope in ["all", "commercial"]:
    keep = set(select(PUB, scope, "balanced", "none").UNIT.unique())
    for y in range(2011, 2026):
        dd = ann[ann.UNIT.isin(keep) & (ann.YEAR == y)]
        m = sm.OLS(dd.g, sm.add_constant(dd.lag)).fit(cov_type="HC3")
        path.append(dict(scope=scope, year=y, beta=float(m.params["lag"]), lo=float(m.conf_int().loc["lag"].iloc[0]),
                         hi=float(m.conf_int().loc["lag"].iloc[1]), p=float(m.pvalues["lag"])))
path = pd.DataFrame(path); path.to_csv(f"{OUT}/annual_slopes.csv", index=False)
R["annual_slopes_negative_share_pre"] = {s: float((g[(g.year <= 2019)].beta < 0).mean()) for s, g in path.groupby("scope")}

# ---- 8c. emissions per departure (one-line check of what convergence in totals does and does not mean)
INT = {}
for y in (2019, 2025):
    t = PUB[PUB.YEAR == y]; INT[f"per_departure_{y}"] = float(t.CO2.sum() / t.TF.sum())
INT["per_departure_change_pct"] = 100*(INT["per_departure_2025"]/INT["per_departure_2019"]-1)
for scope in ["all", "commercial"]:
    dd = select(PUB, scope, "balanced", "none").copy()
    a = dd[(dd.MONTH == 1) & (dd.YEAR == 2019)].groupby("UNIT")[["CO2", "TF"]].sum()
    b = dd[(dd.MONTH == 1) & (dd.YEAR == 2026)].groupby("UNIT")[["CO2", "TF"]].sum()
    idx = a.index.intersection(b.index); ia = np.log(a.CO2[idx]/a.TF[idx]); ib = np.log(b.CO2[idx]/b.TF[idx])
    m = sm.OLS((ib-ia)/7, sm.add_constant(ia)).fit()
    INT[f"{scope}|jan"] = dict(beta=float(m.params.iloc[1]), p=float(m.pvalues.iloc[1]), ci=[float(v) for v in m.conf_int().iloc[1]], n=int(len(ia)))
R["intensity"] = INT
sig = {}
for scope in ["all", "commercial"]:
    keep = set(select(PUB, scope, "balanced", "none").UNIT.unique())
    s = ann[ann.UNIT.isin(keep)].groupby("YEAR").lnE.std(ddof=1)
    base10 = PUB[(PUB.YEAR == 2010) & PUB.UNIT.isin(keep)].groupby("UNIT").CO2.sum()
    s.loc[2010] = np.std(np.log(base10), ddof=1)
    sig[scope] = s.sort_index()
sigdf = pd.DataFrame(sig); sigdf.to_csv(f"{OUT}/sigma_annual.csv")
R["sigma_annual"] = {k: {int(y): float(v) for y, v in s.items()} for k, s in sig.items()}

# ---------------------------------------------------------------- 9. volatility, matched periods, bootstrap
core = select(PUB, "commercial", "balanced", "none")
pv = core.pivot_table(index="TM", columns="UNIT", values="CO2")
size = np.log(pv.loc[(pv.index >= 2010*12) & (pv.index < 2011*12)].mean())
yoy = np.log(pv).diff(12)
jan = core[core.MONTH == 1].pivot_table(index="YEAR", columns="UNIT", values="CO2")
dj = np.log(jan).diff()
def slope_ci(v, s, B=2000):
    s = s[v.index]; r = stats.linregress(s, v)
    bs = []
    idx = np.arange(len(v))
    for _ in range(B):
        k = RNG.choice(idx, len(idx), replace=True)
        bs.append(stats.linregress(s.values[k], v.values[k]).slope)
    return dict(slope=float(r.slope), p=float(r.pvalue), r2=float(r.rvalue**2), ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                small10=float(v[s.nsmallest(10).index].mean()), large10=float(v[s.nlargest(10).index].mean()))
V = {}
V["monthly_2011_2019"] = slope_ci(yoy[(yoy.index >= 2011*12) & (yoy.index < 2020*12)].std(), size)
V["january_2011_2019"] = slope_ci(dj.loc[2011:2019].std(), size)
V["monthly_2011_2025"] = slope_ci(yoy[(yoy.index >= 2011*12) & (yoy.index < 2026*12)].std(), size)
V["january_2011_2025"] = slope_ci(dj.loc[2011:2025].std(), size)
R["volatility"] = V
pd.DataFrame({"size_ln2010": size, "vol_monthly_2011_2019": yoy[(yoy.index >= 2011*12) & (yoy.index < 2020*12)].std(),
              "vol_january_2011_2019": dj.loc[2011:2019].std()}).to_csv(f"{OUT}/volatility.csv")

# ---------------------------------------------------------------- 10. crosswalk
ISO = {"ALBANIA": "ALB", "ARMENIA": "ARM", "AUSTRIA": "AUT", "BELGIUM": "BEL", "BOSNIA AND HERZEGOVINA": "BIH", "BULGARIA": "BGR",
       "CANARY ISLANDS": "ESP (ES-CN)", "CROATIA": "HRV", "CYPRUS": "CYP", "CZECHIA": "CZE", "DENMARK": "DNK", "ESTONIA": "EST",
       "FINLAND": "FIN", "FRANCE": "FRA", "GEORGIA": "GEO", "GERMANY": "DEU", "GREECE": "GRC", "HUNGARY": "HUN", "ICELAND": "ISL",
       "IRELAND": "IRL", "ITALY": "ITA", "KOSOVO": "XKX (user-assigned)", "LATVIA": "LVA", "LIECHTENSTEIN": "LIE", "LITHUANIA": "LTU",
       "LUXEMBOURG": "LUX", "MALTA": "MLT", "MOLDOVA, REPUBLIC OF": "MDA", "MONACO": "MCO", "MONTENEGRO": "MNE", "NETHERLANDS": "NLD",
       "NORTH MACEDONIA": "MKD", "NORWAY": "NOR", "POLAND": "POL", "PORTUGAL": "PRT", "ROMANIA": "ROU", "SERBIA": "SRB", "SLOVAKIA": "SVK",
       "SLOVENIA": "SVN", "SPAIN": "ESP (excl. ES-CN)", "SWEDEN": "SWE", "SWITZERLAND": "CHE", "TÜRKIYE": "TUR", "UNITED KINGDOM": "GBR"}
NOTES = {"UNITED KINGDOM": "includes Jersey, Guernsey, Isle of Man", "CYPRUS": "includes UK Sovereign Base Areas (NOTE not set)",
         "NORWAY": "includes Jan Mayen and Svalbard", "DENMARK": "includes Faroe Islands", "PORTUGAL": "includes Azores and Madeira",
         "SPAIN": "excludes Canary Islands", "CANARY ISLANDS": "reported separately from Spain", "FRANCE": "excludes overseas territories",
         "SERBIA": "shares ICAO prefix LY with Montenegro", "MONTENEGRO": "shares ICAO prefix LY with Serbia",
         "SWITZERLAND": "shares ICAO prefix LS with Liechtenstein", "LIECHTENSTEIN": "shares ICAO prefix LS; sporadic (13 months)",
         "MONACO": "heliport only; < 2 IFR departures per day"}
cw = raw.groupby("STATE_NAME").agg(STATE_CODE=("STATE_CODE", "first"), first=("TM", "min"), last=("TM", "max"), months=("TM", "nunique"), NOTE=("FLAG", "max")).reset_index()
cw["first"] = cw["first"].apply(lambda t: f"{t//12}-{t%12+1:02d}"); cw["last"] = cw["last"].apply(lambda t: f"{t//12}-{t%12+1:02d}")
cw["ISO3166_1"] = cw.STATE_NAME.map(ISO); cw["territorial_note"] = cw.STATE_NAME.map(NOTES).fillna("")
cw["documented_aggregation"] = cw.STATE_NAME.isin(DOC_AGG).astype(int)
cw["valid_from"] = cw["first"]; cw["valid_to"] = cw["last"]; cw["vintage"] = "2026-07-04"
cw.to_csv(f"{OUT}/crosswalk.csv", index=False)
assert cw.ISO3166_1.notna().all()

def conv(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    return str(o)
json.dump(R, open(f"{OUT}/results.json", "w"), indent=1, default=conv, ensure_ascii=False)
print(json.dumps({k: R[k] for k in ["multiverse", "stress_tests", "influence", "jackknife", "panel", "volatility"]}, indent=1, default=conv, ensure_ascii=False))
