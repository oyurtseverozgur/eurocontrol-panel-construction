"""Transformation tests for the EUROCONTROL CO2 audit (run: pytest -q from the package root)."""
import glob, hashlib, json, os
import pandas as pd
import pytest

FILES = sorted(glob.glob("data/raw/co2_emmissions_by_state_*.csv"))

def load():
    d = pd.concat([pd.read_csv(f, encoding="utf-8") for f in FILES], ignore_index=True)
    d["STATE_NAME"] = d["STATE_NAME"].astype(str).str.strip()
    return d

def test_vintage_hashes():
    expected = dict(l.split()[::-1] for l in open("data/raw/SHA256SUMS.txt") if l.strip())
    for f in FILES:
        assert hashlib.sha256(open(f, "rb").read()).hexdigest() == expected[os.path.basename(f)]

def test_record_counts():
    d = load()
    assert len(FILES) == 17 and len(d) == 8337
    assert d.STATE_NAME.nunique() == 44
    assert (d.YEAR * 12 + d.MONTH).nunique() == 197

def test_entity_month_key_unique():
    assert not load().duplicated(["YEAR", "MONTH", "STATE_NAME"]).any()

def test_shared_codes_documented():
    d = load()
    shared = d.groupby("STATE_CODE").STATE_NAME.nunique()
    assert set(shared[shared > 1].index) == {"LY", "LS"}

def test_schema_change_2019():
    cols = {int(f[-8:-4]): list(pd.read_csv(f, nrows=1).columns) for f in FILES}
    assert all(("FLIGHT_MONTH" in c) == (y >= 2019) for y, c in cols.items())

def test_encoding_trap():
    bad = pd.concat([pd.read_csv(f, encoding="cp1252") for f in FILES])
    assert "TÜRKIYE" not in set(bad.STATE_NAME.str.strip())
    assert "TÜRKIYE" in set(load().STATE_NAME)

def test_partial_final_year():
    d = load()
    assert d[d.YEAR == 2026].MONTH.nunique() == 5

def test_note_flag_states():
    d = load()
    flagged = set(d.loc[d.NOTE.astype(str).str.upper() == "TRUE", "STATE_NAME"])
    assert flagged == {"DENMARK", "NORWAY", "PORTUGAL", "UNITED KINGDOM"}

@pytest.mark.skipif(not os.path.exists("out/results.json"), reason="run analysis_v2.py first")
def test_headline_results():
    R = json.load(open("out/results.json"))
    M = R["multiverse"]
    assert M["n_specs"] == 256 and M["all_negative"]
    assert abs(M["by_scope"]["commercial"]["beta_median"] + 0.0097) < 5e-4

@pytest.mark.skipif(not os.path.exists("out/results.json"), reason="run analysis.py first")
def test_pre_pandemic_and_intensity():
    R = json.load(open("out/results.json"))
    pre = R["pre_pandemic"]["commercial|jan|2012-2019"]["beta"]
    assert -0.0125 < pre < -0.0100                                # same-horizon pre-pandemic slope
    assert abs(R["pre_pandemic"]["commercial|difference"]["beta"]) < 0.005
    assert R["intensity"]["commercial|jan"]["p"] > 0.05            # no convergence in CO2 per departure
