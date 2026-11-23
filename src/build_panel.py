"""Step 5: clean the raw SSDS downloads and build 5-year panels.

Usage:
    python src/build_panel.py

Outputs (data/processed/):
    pref_yearly.parquet  wide table, one row per prefecture (and national) x year, derived rates
    pref_panel.parquet   one row per prefecture x 5-year period (1980->85 ... 2015->20)
    muni_panel.parquet   one row per municipality x 5-year period (1995->2000 ... 2015->20)
    pref_start_2020.parquet, muni_start_2020.parquet  features at 2020, for forecasting

Conventions (see docs/datasets.md for the reasons):
- Period t->t+5 runs from the 1 Oct t population count to the 1 Oct t+5 count. Births and
  deaths are summed over years t+1..t+5, which matched the population change best.
- Targets, as % of the population at t over the whole 5 years:
    growth  = (P[t+5] - P[t]) / P[t]
    natural = (births - deaths) / P[t]
    social  = growth - natural  (residual net migration, includes foreign residents)
- Features are measured at the start of the period (year t). Variables only collected in
  survey years (census, housing survey) take the latest value from years <= t, at most
  `MAX_LAG` years old.
- D1: Fukushima is dropped from periods starting 2010 or later.
- D5: designated-city wards are dropped (the city itself is kept); Tokyo's 23 wards are kept.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import geo
from estat import ROOT

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
MAX_LAG = 5
NATIONAL = "00000"
FUKUSHIMA = "07"


def wide(path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    names = df.drop_duplicates("area_code").set_index("area_code")[
        [c for c in ("area_name", "area_level") if c in df]]
    w = df.pivot_table(index=["area_code", "year"], columns="variable", values="value").reset_index()
    w.columns.name = None
    return w.merge(names, left_on="area_code", right_index=True)


def asof(w: pd.DataFrame, col: str, max_lag: int = MAX_LAG) -> pd.Series:
    """Latest non-missing value of `col` from the same or earlier years (within max_lag)."""
    s = w[["area_code", "year", col]].copy()
    s["_src"] = s["year"].where(s[col].notna())
    s[["_v", "_src"]] = s.groupby("area_code")[[col, "_src"]].ffill()
    return s["_v"].where(s["year"] - s["_src"] <= max_lag)


def period_targets(w: pd.DataFrame, starts: list[int]) -> pd.DataFrame:
    """5-year growth / natural / social change for each area and period start t."""
    idx = w.set_index(["area_code", "year"])
    pop, births, deaths = idx["population"], idx["births"], idx["deaths"]
    rows = []
    for t in starts:
        p0 = pop.xs(t, level="year")
        years = pop.index.get_level_values("year")
        p1 = pop.xs(t + 5, level="year") if (t + 5) in years else pd.Series(np.nan, index=p0.index)
        yrs = range(t + 1, t + 6)
        sel = births.index.get_level_values("year").isin(yrs)
        b = births[sel].groupby(level="area_code").agg(lambda s: s.sum(min_count=5))
        d = deaths[sel].groupby(level="area_code").agg(lambda s: s.sum(min_count=5))
        r = pd.DataFrame({"pop_start": p0, "pop_end": p1, "births_5y": b, "deaths_5y": d})
        r["period"] = t
        rows.append(r)
    out = pd.concat(rows).reset_index().rename(columns={"index": "area_code"})
    out["growth"] = (out.pop_end - out.pop_start) / out.pop_start * 100
    out["natural"] = (out.births_5y - out.deaths_5y) / out.pop_start * 100
    out["social"] = out.growth - out.natural
    return out


# --------------------------------------------------------------------------- prefecture

def build_pref() -> tuple[pd.DataFrame, pd.DataFrame]:
    w = wide(RAW / "ssds_pref.parquet").sort_values(["area_code", "year"]).reset_index(drop=True)
    w["pref"] = w.area_code.str[:2]

    # Census-only / survey-year counts and rates -> carry forward to non-survey years.
    for col in ["unmarried_f_30_34", "did_population", "unemployment_rate", "vacancy_rate", "doctors"]:
        w[col] = asof(w, col)
    # All period starts (1980, 1985, ...) are census years, so census-only counts such as
    # unmarried_f_30_34 line up with the yearly female_30_34 denominator at those years.

    w["aging_rate"] = w.pop_65plus / w.population * 100
    w["young_women_share"] = w[["female_20_24", "female_25_29", "female_30_34", "female_35_39"]].sum(
        axis=1, min_count=4) / w.population * 100
    w["unmarried_f_30_34_rate"] = w.unmarried_f_30_34 / w.female_30_34 * 100
    w["did_share"] = w.did_population / w.population * 100
    w["doctors_per_100k"] = w.doctors / w.population * 1e5
    w["log_population"] = np.log(w.population.where(w.population > 0))
    w["income_per_taxpayer"] = w.taxable_income / w.taxpayers  # thousand yen
    w["univ_outflow_share"] = w.univ_entrants_other_pref / w.univ_entrants_total * 100

    # Nominal money values -> relative to the national level in the same year (removes inflation).
    nat = w[w.area_code == NATIONAL].set_index("year")["income_per_taxpayer"]
    w["income_rel"] = w.income_per_taxpayer / w.year.map(nat) * 100
    lp_mean = w[w.area_code != NATIONAL].groupby("year")["land_price_res"].mean()
    w["land_price_rel"] = w.land_price_res / w.year.map(lp_mean) * 100

    # Snow is noisy year to year: 5-year trailing mean.
    w["snow_days_5y"] = w.groupby("area_code")["snow_days"].transform(lambda s: s.rolling(5, min_periods=3).mean())

    yearly = w.merge(geo.pref_table(), on="pref", how="left")

    feats = ["aging_rate", "young_women_share", "tfr", "unmarried_f_30_34_rate", "income_rel",
             "job_openings_ratio", "unemployment_rate", "did_share", "vacancy_rate", "land_price_rel",
             "univ_outflow_share", "hs_grads_jobs_other_pref", "univ_capacity_index", "local_univ_entry_share",
             "doctors_per_100k", "fiscal_strength", "snow_days_5y", "log_population"]
    pw = w[w.area_code != NATIONAL]
    tg = period_targets(pw, list(range(1980, 2025, 5)))  # 2020 start = forecast rows (no target yet)
    start = pw[["area_code", "year", *feats]].rename(columns={"year": "period"})
    panel = tg.merge(start, on=["area_code", "period"], how="left")
    panel["pref"] = panel.area_code.str[:2]
    panel = panel.merge(geo.pref_table(), on="pref", how="left")

    panel["disaster_2011"] = ((panel.period == 2010) & panel.pref.isin(["03", "04"])).astype(int)  # Iwate, Miyagi
    panel["univ_data_available"] = panel.univ_outflow_share.notna().astype(int)
    panel = panel[~((panel.pref == FUKUSHIMA) & (panel.period >= 2010))]  # D1
    panel["period_label"] = panel.period.astype(str) + "-" + (panel.period + 5).astype(str)
    panel = panel.reset_index(drop=True)
    return yearly, panel[panel.period < 2020].reset_index(drop=True), panel[panel.period == 2020].reset_index(drop=True)


# --------------------------------------------------------------------------- municipality

def build_muni(pref_yearly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    w = wide(RAW / "ssds_muni.parquet").sort_values(["area_code", "year"]).reset_index(drop=True)

    # D5: keep cities/towns/villages; drop designated-city wards and the all-Tokyo-wards
    # aggregate (13100), keep the 23 Tokyo special wards.
    tokyo_wards = w.area_code.between("13101", "13123")
    keep = ((w.area_level == "2") & (w.area_code != "13100")) | tokyo_wards
    w = w[keep].copy()
    w["pref"] = w.area_code.str[:2]

    # Counts reported as '-' (no DID in this municipality) mean zero, not missing.
    w["did_population"] = w.did_population.where(w.population.isna() | w.did_population.notna(), 0)
    for col in ["vacancy_rate", "unemployment_rate", "did_population", "female_15_64", "pop_65plus", "doctors"]:
        w[col] = asof(w, col)

    w["aging_rate"] = w.pop_65plus / w.population * 100
    w["working_women_share"] = w.female_15_64 / w.population * 100
    w["did_share"] = w.did_population / w.population * 100
    w["doctors_per_1k"] = w.doctors / w.population * 1e3
    w["log_population"] = np.log(w.population.where(w.population > 0))
    nat = pref_yearly[pref_yearly.area_code == NATIONAL].set_index("year")["income_per_taxpayer"]
    w["income_rel"] = (w.taxable_income / w.taxpayers) / w.year.map(nat) * 100

    feats = ["aging_rate", "working_women_share", "income_rel", "unemployment_rate", "did_share",
             "vacancy_rate", "doctors_per_1k", "fiscal_strength", "log_population"]
    tg = period_targets(w, list(range(1995, 2025, 5)))  # 2020 start = forecast rows
    start = w[["area_code", "year", "area_name", *feats]].rename(columns={"year": "period"})
    panel = tg.merge(start, on=["area_code", "period"], how="left")
    panel["pref"] = panel.area_code.str[:2]
    panel = panel.merge(geo.pref_table()[["pref", "pref_name", "region", "dist_tokyo_km", "dist_metro_km"]],
                        on="pref", how="left")
    panel = panel[~((panel.pref == FUKUSHIMA) & (panel.period >= 2010))]  # D1
    # Same logic as D1: Miyake village (13381) was fully evacuated after the 2000 eruption
    # (census 2000 population = 0), so drop the two periods touching 2000.
    panel = panel[~((panel.area_code == "13381") & panel.period.isin([1995, 2000]))]
    panel["period_label"] = panel.period.astype(str) + "-" + (panel.period + 5).astype(str)
    future = panel[(panel.period == 2020) & (panel.pop_start > 0)].reset_index(drop=True)
    panel = panel[panel.period < 2020].dropna(subset=["growth", "natural"])
    return panel.reset_index(drop=True), future


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    yearly, pref, pref_2020 = build_pref()
    muni, muni_2020 = build_muni(yearly)
    yearly.to_parquet(OUT / "pref_yearly.parquet", index=False)
    pref.to_parquet(OUT / "pref_panel.parquet", index=False)
    muni.to_parquet(OUT / "muni_panel.parquet", index=False)
    # Start-of-period features for 2020 (targets unknown) -> used by the forecast in step 8.
    pref_2020.to_parquet(OUT / "pref_start_2020.parquet", index=False)
    muni_2020.to_parquet(OUT / "muni_start_2020.parquet", index=False)

    for name, df in [("pref_panel", pref), ("muni_panel", muni)]:
        print(f"\n{name}: {len(df):,} rows, {df.area_code.nunique()} areas, periods {sorted(df.period.unique())}")
        miss = df.isna().mean().mul(100).round(1)
        print("  % missing:", miss[miss > 0].to_dict())


if __name__ == "__main__":
    main()
