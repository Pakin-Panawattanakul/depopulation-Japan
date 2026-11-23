"""Feature lists and transforms shared by steps 7-9."""

from __future__ import annotations

import numpy as np
import pandas as pd

from estat import ROOT

PROC = ROOT / "data" / "processed"
TARGETS = ["natural", "social"]

# Prefecture candidates. univ_outflow_share only exists from 2000 (D4), so it is in a
# separate list for the post-2000 models.
PREF_FEATURES = [
    "aging_rate", "young_women_share", "tfr", "unmarried_f_30_34_rate",           # demography
    "income_rel", "job_openings_ratio", "unemployment_rate",                      # economy
    "did_share", "log_dist_metro", "log_population",                               # urban / geography
    "vacancy_rate", "log_land_price_rel",                                          # housing
    "hs_grads_jobs_other_pref", "univ_capacity_index",                             # education
    "doctors_per_100k", "fiscal_strength", "snow_days_5y",                         # health, finance, climate
]
PREF_FEATURES_POST2000 = PREF_FEATURES + ["univ_outflow_share"]

MUNI_FEATURES = ["aging_rate", "income_rel", "unemployment_rate", "did_share", "log_population",
                 "doctors_per_1k", "fiscal_strength", "log_dist_metro"]
MUNI_FEATURES_EXTRA = MUNI_FEATURES + ["working_women_share", "vacancy_rate"]  # shorter coverage

LABELS = {
    "aging_rate": "Aging rate (65+ %)", "young_women_share": "Women 20–39 (% of pop.)",
    "working_women_share": "Women 15–64 (% of pop.)", "tfr": "Total fertility rate",
    "unmarried_f_30_34_rate": "Unmarried women 30–34 (%)", "income_rel": "Income per taxpayer (Japan=100)",
    "job_openings_ratio": "Job-openings ratio", "unemployment_rate": "Unemployment rate",
    "did_share": "Urban share (DID %)", "log_dist_metro": "Distance to nearest metro (log)",
    "log_population": "Population size (log)", "vacancy_rate": "Vacant housing (%)",
    "log_land_price_rel": "Land price (log, rel.)", "hs_grads_jobs_other_pref": "HS grads taking jobs elsewhere (%)",
    "univ_capacity_index": "University capacity index", "univ_outflow_share": "Univ. entrants leaving pref. (%)",
    "doctors_per_100k": "Doctors per 100k", "doctors_per_1k": "Doctors per 1k",
    "fiscal_strength": "Fiscal strength index", "snow_days_5y": "Snow days per year",
    "disaster_2011": "2011 disaster (Iwate, Miyagi)",
}


def add_transforms(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["log_dist_metro"] = np.log1p(df["dist_metro_km"])
    if "land_price_rel" in df:
        df["log_land_price_rel"] = np.log(df["land_price_rel"])
    return df


def load_pref() -> pd.DataFrame:
    return add_transforms(pd.read_parquet(PROC / "pref_panel.parquet"))


def load_muni() -> pd.DataFrame:
    return add_transforms(pd.read_parquet(PROC / "muni_panel.parquet"))


def demean_by(df: pd.DataFrame, cols: list[str], by: str = "period") -> pd.DataFrame:
    """Subtract the group mean (e.g. period fixed effect) from each column."""
    return df[cols] - df.groupby(by)[cols].transform("mean")
