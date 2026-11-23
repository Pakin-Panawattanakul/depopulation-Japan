"""Step 11: why are fewer babies born? (drivers of low fertility, prefecture level)

Usage:
    python src/fertility.py          # after download.py (variables tagged 'fertility' in config/variables.csv)

In Japan about 98% of births are to married parents, so fewer births can come from
  (a) fewer women being married (later / no marriage), or
  (b) married couples having fewer children.
The script
  1. Splits the decline exactly into those two parts:
         births per 1,000 women 20-44 (GFR) = married share of women 20-44 x births per 1,000 married women (GMFR)
     and checks the result with an age-by-age version for 1980-2005 (births by mother's age stop in 2007).
  2. Regresses three outcomes on economic, women's-work, housing, childcare, family and urban variables:
         total fertility rate (TFR), married share of women 25-39, births per married woman (GMFR).
     Spec A: year fixed effects (compare prefectures in the same census year).
     Spec B: year + prefecture fixed effects (does a prefecture's fertility follow its own changes?).
  3. Shapley R² by *theme*, so the answer to "economy or housing?" doesn't depend on which single
     variable in a theme happens to win.
Unit: prefecture x census year 1985-2020 (income data starts 1985). Outcomes and features are measured in
the same census year (births averaged over t-1..t+1), so results are associations, not causal effects.

Outputs: reports/fertility.md, reports/fertility_*.csv, figures 21-24.
"""

from __future__ import annotations

from itertools import combinations
from math import factorial

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import geo
import plotstyle as ps
from build_panel import NATIONAL, RAW, asof, wide
from estat import ROOT

CENSUS = list(range(1985, 2025, 5))
AGES = ["20_24", "25_29", "30_34", "35_39", "40_44"]

THEMES = {
    "Economy": ["income_rel", "wage_m_rel", "job_openings_ratio", "unemployment_rate"],
    "Women's work": ["female_lfp", "gender_wage_ratio", "dual_income_rate"],
    "Housing": ["homeownership_rate", "floor_area_owned", "rent_rel", "long_commute_share"],
    "Childcare": ["childcare_use_rate", "nurseries_per_child"],
    "Family structure": ["nuclear_family_share"],
    "Urbanization": ["did_share"],
}
FEATS = [f for fs in THEMES.values() for f in fs]
TARGETS = {
    "tfr": "Total fertility rate",
    "married_share_25_39": "Married share of women 25–39 (%)",
    "gmfr": "Births per 1,000 married women 20–44",
}
LABELS = {
    "income_rel": "Income per taxpayer (Japan=100)", "wage_m_rel": "Men's wage (Japan=100)",
    "job_openings_ratio": "Job-openings ratio", "unemployment_rate": "Unemployment rate",
    "female_lfp": "Women's labor-force participation (%)", "gender_wage_ratio": "Women's wage / men's wage (%)",
    "dual_income_rate": "Married couples with both working (%)", "homeownership_rate": "Home ownership (%)",
    "floor_area_owned": "Floor area of owned homes (m²)", "rent_rel": "Private rent (pref. avg = 100)",
    "long_commute_share": "Long commutes, 90+ min (per 1,000)", "childcare_use_rate": "Nursery usage rate (%)",
    "nurseries_per_child": "Nurseries per 100k children", "nuclear_family_share": "Nuclear-family households (%)",
    "did_share": "Urban share (DID %)", "univ_rate_f": "Women's university entry rate (%)",
    "waitlist_per_1k_births": "Nursery waiting list per 1,000 births",
}


# --------------------------------------------------------------------------- data

def build() -> pd.DataFrame:
    w = wide(RAW / "ssds_pref.parquet").sort_values(["area_code", "year"]).reset_index(drop=True)
    w["pref"] = w.area_code.str[:2]
    w["wage_m"] = w.wage_m.fillna(w.wage_m_2020)
    w["wage_f"] = w.wage_f.fillna(w.wage_f_2020)
    survey = ["homeownership_rate", "floor_area_owned", "floor_area_rented", "long_commute_share",
              "dual_income_households", "married_f_15plus", "labor_force_f", "not_in_labor_force_f", "nuclear_family_share",
              "did_population", "unemployment_rate", "nurseries_per_child"] + [f"married_f_{a}" for a in AGES]
    for c in survey:
        w[c] = asof(w, c)

    g = w.groupby("area_code")
    w["births_3y"] = g.births.transform(lambda s: s.rolling(3, center=True, min_periods=1).mean())
    w["tfr"] = g.tfr.transform(lambda s: s.rolling(3, center=True, min_periods=1).mean())
    w["women_20_44"] = w[[f"female_{a}" for a in AGES]].sum(axis=1, min_count=5)
    w["married_20_44"] = w[[f"married_f_{a}" for a in AGES]].sum(axis=1, min_count=5)
    w["married_share_20_44"] = w.married_20_44 / w.women_20_44 * 100
    w["married_share_25_39"] = (w[[f"married_f_{a}" for a in AGES[1:4]]].sum(axis=1, min_count=3)
                                / w[[f"female_{a}" for a in AGES[1:4]]].sum(axis=1, min_count=3) * 100)
    w["gfr"] = w.births_3y / w.women_20_44 * 1000
    w["gmfr"] = w.births_3y / w.married_20_44 * 1000

    nat = w[w.area_code == NATIONAL].set_index("year")
    w["income_rel"] = (w.taxable_income / w.taxpayers) / w.year.map(nat.taxable_income / nat.taxpayers) * 100
    w["wage_m_rel"] = w.wage_m / w.year.map(nat.wage_m) * 100
    w["gender_wage_ratio"] = w.wage_f / w.wage_m * 100
    # Dual-income households per married couple (married women 15+). SSDS's own ratio (#F01503) divides
    # by all households, which mechanically rises with the married share, so it would partly measure marriage.
    w["dual_income_rate"] = w.dual_income_households / w.married_f_15plus * 100
    w["female_lfp"] = w.labor_force_f / (w.labor_force_f + w.not_in_labor_force_f) * 100
    rent_mean = w[w.area_code != NATIONAL].groupby("year").rent_private.mean()
    w["rent_rel"] = w.rent_private / w.year.map(rent_mean) * 100
    w["did_share"] = w.did_population / w.population * 100
    w["waitlist_per_1k_births"] = w.waitlisted_children / w.births_3y * 1000
    return w.merge(geo.pref_table()[["pref", "pref_name", "region"]], on="pref", how="left")


# --------------------------------------------------------------------------- 1. decomposition

def decomposition(w: pd.DataFrame, L: list[str]) -> pd.DataFrame:
    n = w[(w.area_code == NATIONAL) & w.year.isin([1980, *CENSUS])].set_index("year")
    base = n.loc[1980]
    rows = []
    for yr in [1980, *CENSUS]:
        r = n.loc[yr]
        rows.append({"year": yr, "tfr": r.tfr, "gfr": r.gfr, "married_share_20_44": r.married_share_20_44,
                     "married_share_25_39": r.married_share_25_39, "gmfr": r.gmfr,
                     "ln_gfr": np.log(r.gfr / base.gfr), "ln_marriage": np.log(r.married_share_20_44 / base.married_share_20_44),
                     "ln_marital": np.log(r.gmfr / base.gmfr)})
    d = pd.DataFrame(rows)
    d.round(4).to_csv(ROOT / "reports" / "fertility_national.csv", index=False)

    # Age-by-age check, 1980 -> 2005 (births by mother's age exist only to 2007).
    def by_age(yr):
        r = n.loc[yr]
        m = np.array([r[f"married_f_{a}"] / r[f"female_{a}"] for a in AGES])
        bcols = {"20_24": "births_m20_24", "25_29": "births_m25_29", "30_34": "births_m30_34",
                 "35_39": "births_m35_39", "40_44": "births_m40_44"}
        raw = pd.read_parquet(RAW / "ssds_pref.parquet").query("area_code == @NATIONAL")
        bm = raw[raw.variable.str.startswith("births_m")].pivot_table(index="year", columns="variable", values="value")
        b = np.array([bm.loc[yr - 1:yr + 1, bcols[a]].mean() for a in AGES]) if not bm.empty else None
        g_ = b / np.array([r[f"married_f_{a}"] for a in AGES])
        return m, g_
    age_note = ""
    try:
        m1, g1 = by_age(1980)
        m2, g2 = by_age(2005)
        tfr1, tfr2 = 5 * (m1 * g1).sum(), 5 * (m2 * g2).sum()
        marr = 5 * ((m2 - m1) * (g1 + g2) / 2).sum()
        marit = 5 * ((g2 - g1) * (m1 + m2) / 2).sum()
        age_note = (f"Age-by-age check, 1980→2005 (Kitagawa decomposition over five 5-year age groups): "
                    f"TFR {tfr1:.2f} → {tfr2:.2f} ({tfr2 - tfr1:+.2f}); fewer married women {marr:+.2f}, "
                    f"births per married woman {marit:+.2f}, so **{marr / (tfr2 - tfr1):.0%} of the decline came from marriage**.")
    except Exception as e:  # births-by-age items are optional
        age_note = f"(Age-by-age check skipped: {e})"

    # Per prefecture, 1985 -> 2020.
    p = w[(w.area_code != NATIONAL) & w.year.isin([1985, 2020])].pivot_table(
        index="pref_name", columns="year", values=["gfr", "married_share_20_44", "gmfr", "tfr"])
    pp = pd.DataFrame({
        "tfr_1985": p[("tfr", 1985)], "tfr_2020": p[("tfr", 2020)],
        "ln_gfr": np.log(p[("gfr", 2020)] / p[("gfr", 1985)]),
        "ln_marriage": np.log(p[("married_share_20_44", 2020)] / p[("married_share_20_44", 1985)]),
        "ln_marital": np.log(p[("gmfr", 2020)] / p[("gmfr", 1985)]),
    })
    pp["marriage_share_of_decline"] = pp.ln_marriage / pp.ln_gfr
    pp.round(4).to_csv(ROOT / "reports" / "fertility_by_prefecture.csv")

    last = d.set_index("year").loc[2020]
    mid = d.set_index("year").loc[2000]
    L += ["## 1. Fewer marriages, or fewer children per marriage?", "",
          "Exact split: births per 1,000 women aged 20–44 = (share of women 20–44 who are married) × "
          "(births per 1,000 married women 20–44). In log terms the two parts add up exactly.", "",
          "| Year | TFR | Births per 1,000 women 20–44 | Married share 20–44 | Married share 25–39 | Births per 1,000 married women |",
          "|---|---|---|---|---|---|"]
    for r in d.itertuples():
        L.append(f"| {r.year} | {r.tfr:.2f} | {r.gfr:.1f} | {r.married_share_20_44:.1f}% | "
                 f"{r.married_share_25_39:.1f}% | {r.gmfr:.1f} |")
    L += ["",
          f"- **1980→2000:** births per woman fell {1 - np.exp(mid.ln_gfr):.0%}. Marriage part {mid.ln_marriage:+.3f}, "
          f"within-marriage part {mid.ln_marital:+.3f} (log points).",
          f"- **1980→2020:** births per woman fell {1 - np.exp(last.ln_gfr):.0%}. Marriage part {last.ln_marriage:+.3f}, "
          f"within-marriage part {last.ln_marital:+.3f}.",
          f"- {age_note}",
          f"- Across prefectures, 1985→2020: the marriage part is larger than the total decline in "
          f"{(pp.marriage_share_of_decline > 1).sum()} of 47 prefectures, because births *per married woman* rose there. "
          f"Median share of the decline due to marriage: {pp.marriage_share_of_decline.median():.0%}.",
          "- Caution: births per married woman can rise partly because the women who still marry are the ones who "
          "want children (selection), so the within-marriage part is a lower bound on how much family size itself fell.", ""]
    return d


# --------------------------------------------------------------------------- 2-3. drivers

def r2(X, y):
    if X.shape[1] == 0:
        return 0.0
    A = np.column_stack([np.ones(len(y)), X])
    b = np.linalg.lstsq(A, y, rcond=None)[0]
    e = y - A @ b
    return 1 - e @ e / ((y - y.mean()) @ (y - y.mean()))


def theme_shapley(X: pd.DataFrame, y: pd.Series) -> pd.Series:
    names = list(THEMES)
    idx = {t: [X.columns.get_loc(f) for f in THEMES[t] if f in X] for t in names}
    cache = {}

    def v(S):
        key = frozenset(S)
        if key not in cache:
            cols = sorted(c for t in S for c in idx[t])
            cache[key] = r2(X.values[:, cols], y.values)
        return cache[key]

    k = len(names)
    out = {}
    for t in names:
        rest = [o for o in names if o != t]
        out[t] = sum(factorial(m) * factorial(k - m - 1) / factorial(k) * (v(set(S) | {t}) - v(set(S)))
                     for m in range(k) for S in combinations(rest, m))
    return pd.Series(out)


def demean(d: pd.DataFrame, cols: list[str], two_way: bool) -> pd.DataFrame:
    x = d[cols] - d.groupby("year")[cols].transform("mean")
    if two_way:  # iterate to convergence (balanced panel -> one pass is exact; loop is cheap insurance)
        for _ in range(20):
            x = x - x.groupby(d.area_code).transform("mean")
            x = x - x.groupby(d.year).transform("mean")
    return x


def drivers(w: pd.DataFrame, L: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = w[(w.area_code != NATIONAL) & w.year.isin(CENSUS)].dropna(subset=FEATS + list(TARGETS)).copy()
    z = d.copy()
    for f in FEATS:
        z[f] = (d[f] - d[f].mean()) / d[f].std()
    coef_rows, shap_rows = [], []
    for t, tl in TARGETS.items():
        for spec, fe, two in [("Between prefectures (year FE)", "C(year)", False),
                              ("Within a prefecture over time (two-way FE)", "C(year) + C(area_code)", True)]:
            m = smf.ols(f"{t} ~ {' + '.join(FEATS)} + {fe}", data=z).fit(
                cov_type="cluster", cov_kwds={"groups": z.area_code})
            ci = m.conf_int()
            for f in FEATS:
                coef_rows.append({"target": t, "spec": spec, "feature": f, "label": LABELS[f],
                                  "theme": next(k for k, v in THEMES.items() if f in v),
                                  "coef": m.params[f], "lo": ci.loc[f, 0], "hi": ci.loc[f, 1], "p": m.pvalues[f]})
            X = demean(z, FEATS, two)
            y = demean(z, [t], two)[t]
            sh = theme_shapley(X, y)
            tot = r2(X.values, y.values)
            for th, v in sh.items():
                shap_rows.append({"target": t, "spec": spec, "theme": th, "shapley_r2": v, "share": v / tot, "r2": tot})
    co, sh = pd.DataFrame(coef_rows), pd.DataFrame(shap_rows)
    co.round(4).to_csv(ROOT / "reports" / "fertility_coefficients.csv", index=False)
    sh.round(4).to_csv(ROOT / "reports" / "fertility_theme_shapley.csv", index=False)

    L += ["## 2. Which themes matter? (Shapley R² by theme)", "",
          f"n = {len(d)} prefecture × census-year observations (1985–2020). Each cell: share of the explained "
          "variance that belongs to the theme (the theme's variables enter together). R² is the variance explained "
          "after removing year (and, for 'within', prefecture) averages.", ""]
    for spec in sh.spec.unique():
        g = sh[sh.spec == spec]
        piv = g.pivot(index="theme", columns="target", values="share").loc[list(THEMES), list(TARGETS)]
        r2s = g.groupby("target").r2.first()
        L += [f"**{spec}**", "", "| Theme | " + " | ".join(TARGETS.values()) + " |", "|---|---|---|---|"]
        for th in THEMES:
            cells = []
            for t in TARGETS:
                v = piv.loc[th, t]
                cells.append(f"**{v:.0%}**" if v == piv[t].max() else f"{v:.0%}")
            L.append(f"| {th} | " + " | ".join(cells) + " |")
        L.append("| *R²* | " + " | ".join(f"{r2s[t]:.2f}" for t in TARGETS) + " |")
        L.append("")

    L += ["## 3. Individual variables (standardized coefficients, 95% CI, clustered by prefecture)", "",
          "Effect of +1 standard deviation of the variable on the outcome, holding the other variables fixed. ✱ = p < 0.05.", ""]
    for t, tl in TARGETS.items():
        L += [f"**{tl}**", "", "| Variable | Theme | Between prefectures | Within a prefecture |", "|---|---|---|---|"]
        g = co[co.target == t]
        a = g[g.spec.str.startswith("Between")].set_index("feature")
        b = g[g.spec.str.startswith("Within")].set_index("feature")
        for f in a.reindex(a.coef.abs().sort_values(ascending=False).index).index:
            cell = lambda r: f"{r.coef:+.3f}{' ✱' if r.p < 0.05 else ''} [{r.lo:+.2f}, {r.hi:+.2f}]"
            L.append(f"| {LABELS[f]} | {a.loc[f, 'theme']} | {cell(a.loc[f])} | {cell(b.loc[f])} |")
        L.append("")
    return co, sh


def post2000(w: pd.DataFrame, L: list[str]) -> None:
    extra = ["univ_rate_f", "waitlist_per_1k_births"]
    d = w[(w.area_code != NATIONAL) & w.year.isin([2005, 2010, 2015, 2020])].dropna(
        subset=FEATS + extra + list(TARGETS)).copy()
    for f in FEATS + extra:
        d[f] = (d[f] - d[f].mean()) / d[f].std()
    L += ["## 4. Extra variables available only after 2000 (between prefectures, year FE)", "",
          f"n = {len(d)}. Coefficients for the two added variables, with all the variables above held fixed:", "",
          "| Outcome | " + " | ".join(LABELS[e] for e in extra) + " |", "|---|---|---|"]
    for t, tl in TARGETS.items():
        m = smf.ols(f"{t} ~ {' + '.join(FEATS + extra)} + C(year)", data=d).fit(
            cov_type="cluster", cov_kwds={"groups": d.area_code})
        ci = m.conf_int()
        L.append(f"| {tl} | " + " | ".join(
            f"{m.params[e]:+.3f}{' ✱' if m.pvalues[e] < 0.05 else ''} [{ci.loc[e, 0]:+.2f}, {ci.loc[e, 1]:+.2f}]"
            for e in extra) + " |")
    L.append("")


# --------------------------------------------------------------------------- figures

def figures(nat: pd.DataFrame, co: pd.DataFrame, sh: pd.DataFrame, w: pd.DataFrame) -> None:
    # 21: national index lines.
    fig, ax = plt.subplots(figsize=(8, 3.8))
    series = [("tfr", "Total fertility rate"), ("married_share_25_39", "Married share, women 25–39"),
              ("gmfr", "Births per married woman 20–44")]
    for i, (c, lab) in enumerate(series):
        v = nat[c] / nat[c].iloc[0] * 100
        ax.plot(nat.year, v, color=ps.SERIES[i], marker="o", markersize=6, markeredgecolor=ps.SURFACE,
                markeredgewidth=1.5)
        ax.text(nat.year.iloc[-1] + 0.8, v.iloc[-1], f"{lab} ({v.iloc[-1]:.0f})", va="center", fontsize=9,
                color=ps.INK_2)
    ax.axhline(100, color=ps.BASELINE, lw=1)
    ax.set_xlim(1979, 2038)
    ax.set_ylabel("Index, 1980 = 100")
    ax.set_title("Japan: marriage fell much more than births per married woman")
    ps.save(fig, "21_fertility_marriage_index")

    # 22: theme Shapley shares, between vs within, per outcome.
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, (t, tl) in zip(axes, TARGETS.items()):
        g = sh[sh.target == t]
        y = np.arange(len(THEMES))
        for k, spec in enumerate(g.spec.unique()):
            v = g[g.spec == spec].set_index("theme").loc[list(THEMES), "share"]
            ax.barh(y + (k - 0.5) * 0.38, v, height=0.36, color=ps.SERIES[k], label=spec)
            for yi, vi in zip(y, v):
                ax.text(vi + 0.01, yi + (k - 0.5) * 0.38, f"{vi:.0%}", va="center", fontsize=7, color=ps.INK_2)
        ax.set_yticks(y, list(THEMES))
        ax.set_xlim(0, max(0.8, sh.share.max() * 1.15))
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.grid(axis="y", visible=False)
        ax.invert_yaxis()
        r2a, r2b = g.groupby("spec", sort=False).r2.first().values
        ax.set_title(f"{tl}\n(R² between {r2a:.2f}, within {r2b:.2f})", fontsize=9.5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.suptitle("Why fewer births? Share of explained variance by theme", x=0.01, ha="left",
                 fontweight="bold", fontsize=11)
    fig.tight_layout()
    fig.subplots_adjust(top=0.68)
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.93), ncol=2, fontsize=9)
    ps.save(fig, "22_fertility_themes")

    # 23: coefficients per outcome (both specs).
    fig, axes = plt.subplots(1, 3, figsize=(13, 6), sharey=True)
    order = (co[(co.target == "tfr") & co.spec.str.startswith("Between")].sort_values("coef").feature.tolist())
    yy = {f: i for i, f in enumerate(order)}
    for ax, (t, tl) in zip(axes, TARGETS.items()):
        g = co[co.target == t]
        for k, spec in enumerate(g.spec.unique()):
            s = g[g.spec == spec]
            off = (k - 0.5) * 0.3
            ys = [yy[f] + off for f in s.feature]
            ax.hlines(ys, s.lo, s.hi, color=ps.SERIES[k], lw=2)
            ax.scatter(s.coef, ys, color=ps.SERIES[k], s=30, zorder=3, edgecolor=ps.SURFACE, linewidth=1.5,
                       label=spec)
        ax.axvline(0, color=ps.BASELINE, lw=1)
        ax.set_title(tl, fontsize=9.5)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Effect of +1 SD (95% CI)")
    axes[0].set_yticks(range(len(order)), [LABELS[f] for f in order], fontsize=8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.suptitle("Variables linked to fertility, marriage and births per married woman (prefectures 1985–2020)",
                 x=0.01, ha="left", fontweight="bold", fontsize=11)
    fig.tight_layout()
    fig.subplots_adjust(top=0.84)
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.955), ncol=2, fontsize=9)
    ps.save(fig, "23_fertility_coefficients")

    # 24: TFR vs married share across prefectures, 2020.
    d = w[(w.area_code != NATIONAL) & (w.year == 2020)]
    fig, ax = plt.subplots(figsize=(6, 4.6))
    ax.scatter(d.married_share_25_39, d.tfr, s=28, color=ps.SERIES[0], edgecolor=ps.SURFACE, linewidth=1.5)
    for r in d.itertuples():
        if r.pref_name in ("Tokyo", "Okinawa", "Kyoto", "Hokkaido", "Shimane", "Fukui", "Miyazaki", "Akita"):
            ax.annotate(r.pref_name, (r.married_share_25_39, r.tfr), xytext=(4, 3), textcoords="offset points",
                        fontsize=8, color=ps.INK_2)
    c = d[["married_share_25_39", "tfr"]].corr().iloc[0, 1]
    ax.set_xlabel("Married share of women 25–39, 2020 (%)")
    ax.set_ylabel("Total fertility rate, 2019–2021")
    ax.set_title(f"Where more women are married, fertility is higher (r = {c:.2f})")
    ps.save(fig, "24_fertility_vs_marriage_2020")


def main() -> None:
    ps.apply()
    w = build()
    L = ["# Step 11: why are fewer babies born?", "",
         "Generated by `python src/fertility.py`; method in the module docstring. Prefecture level.", ""]
    nat = decomposition(w, L)
    co, sh = drivers(w, L)
    post2000(w, L)
    figures(nat, co, sh, w)
    (ROOT / "reports" / "fertility.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
