"""Step 6: exploratory analysis.

Usage:
    python src/eda.py

Writes figures to reports/figures/ and key numbers to reports/eda_summary.json.
Questions answered:
  - How did Japan's population, and its natural vs. social components, evolve?
  - When did each prefecture's population peak (start of sustained decline), and does
    that line up with historical events?
  - How does migration toward the Tokyo area track the economy (bubble, crises, COVID)?
  - Where and how fast are municipalities shrinking?
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import geo
import plotstyle as ps
from estat import ROOT

PROC = ROOT / "data" / "processed"
EVENTS = [(1991, "Bubble bursts"), (2008, "Lehman shock"), (2011, "Tohoku quake"), (2020, "COVID-19")]


def mark_events(ax, ymax_frac=0.97):
    lo, hi = ax.get_ylim()
    for i, (yr, label) in enumerate(EVENTS):
        ax.axvline(yr, color=ps.BASELINE, lw=1, ls=(0, (3, 3)), zorder=0)
        frac = ymax_frac - 0.07 * (i % 2)  # stagger so neighbouring events don't collide
        ax.text(yr + 0.3, lo + (hi - lo) * frac, label, color=ps.MUTED, fontsize=8, va="top")


def national(y: pd.DataFrame, summary: dict) -> None:
    n = y[y.area_code == "00000"].set_index("year")
    peak_year = int(n.population.idxmax())
    summary["national_peak_year"] = peak_year
    summary["national_peak_population"] = int(n.population.max())

    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(n.index, n.population / 1e6, color=ps.SERIES[0])
    ax.scatter([peak_year], [n.population.max() / 1e6], color=ps.SERIES[0], s=40, zorder=3,
               edgecolor=ps.SURFACE, linewidth=2)
    ax.annotate(f"Peak {peak_year}: {n.population.max() / 1e6:.1f}M", (peak_year, n.population.max() / 1e6),
                xytext=(-10, 10), textcoords="offset points", ha="right", color=ps.INK_2, fontsize=9)
    ax.set_title("Japan's population peaked in the late 2000s")
    ax.set_ylabel("Population (millions)")
    ax.set_xlim(1975, 2025)
    ps.save(fig, "01_national_population")

    nat = (n.births - n.deaths) / 1e3
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.axhline(0, color=ps.BASELINE, lw=1)
    ax.plot(nat.dropna().index, nat.dropna(), color=ps.SERIES[1])
    first_neg = int(nat[nat < 0].index.min())
    summary["national_first_natural_decrease_year"] = first_neg
    ax.annotate(f"Deaths exceed births from {first_neg}", (first_neg, 0), xytext=(-12, -30),
                textcoords="offset points", ha="right", color=ps.INK_2, fontsize=9,
                arrowprops=dict(arrowstyle="-", color=ps.MUTED, lw=0.8))
    ax.set_xlim(1975, 2025)
    ax.set_title("Natural change: births minus deaths, Japan")
    ax.set_ylabel("Thousand people per year")
    mark_events(ax)
    ps.save(fig, "02_national_natural_change")


def peaks(y: pd.DataFrame, summary: dict) -> pd.DataFrame:
    p = y[y.area_code != "00000"].dropna(subset=["population"])
    rows = []
    for code, g in p.groupby("area_code"):
        g = g.set_index("year").population
        peak = int(g.idxmax())
        rows.append({"pref": code[:2], "peak_year": peak, "censored": peak == g.index.min(),
                     "still_growing": peak == g.index.max(),
                     "change_since_peak_pct": (g.iloc[-1] / g.max() - 1) * 100})
    pk = pd.DataFrame(rows).merge(geo.pref_table(), on="pref").sort_values("peak_year")

    bins = [(1975, 1975, "Already declining in 1975"), (1976, 1985, "1976–1985"),
            (1986, 1991, "Bubble era 1986–1991"), (1992, 1999, "After the bubble 1992–1999"),
            (2000, 2004, "2000–2004"), (2005, 2010, "2005–2010 (national peak)"),
            (2011, 2019, "2011–2019"), (2020, 2025, "2020 or later / still growing")]
    summary["peak_year_groups"] = {lab: pk[(pk.peak_year >= a) & (pk.peak_year <= b)].pref_name.tolist()
                                   for a, b, lab in bins}

    fig, ax = plt.subplots(figsize=(8, 9.5))
    ypos = np.arange(len(pk))
    ax.hlines(ypos, 1975, pk.peak_year, color=ps.GRID, lw=1)
    ax.scatter(pk.peak_year, ypos, s=36, color=ps.SERIES[0], zorder=3, edgecolor=ps.SURFACE, linewidth=1.5)
    for i, r in enumerate(pk.itertuples()):
        tag = " (≤1975)" if r.censored else (" (still growing)" if r.still_growing else "")
        ax.text(r.peak_year + 0.6, i, f"{r.pref_name}{tag}", va="center", fontsize=8, color=ps.INK_2)
    ax.set_yticks([])
    ax.grid(axis="y", visible=False)
    ax.set_xlim(1974, 2034)
    ax.set_ylim(-1, len(pk))
    ax.invert_yaxis()
    for i, (yr, label) in enumerate(EVENTS):
        ax.axvline(yr, color=ps.BASELINE, lw=1, ls=(0, (3, 3)), zorder=0)
        ax.text(yr, -1.4 - 1.1 * (i % 2), label, color=ps.MUTED, fontsize=8, ha="center")
    ax.set_title("Year each prefecture's population peaked (1975–2024 data)", pad=34)
    ax.set_xlabel("Peak year")
    ps.save(fig, "03_prefecture_peak_year")
    pk.to_csv(ROOT / "reports" / "prefecture_peaks.csv", index=False)
    return pk


def migration_blocs(y: pd.DataFrame, summary: dict) -> None:
    p = y[y.area_code != "00000"].copy()
    bloc = {**{c: "Tokyo area" for c in geo.TOKYO_AREA},
            **{c: "Osaka & Nagoya areas" for c in ["21", "23", "24", "26", "27", "28", "29"]}}
    p["bloc"] = p.pref.map(bloc).fillna("Rest of Japan")
    g = p.groupby(["bloc", "year"])[["moves_in", "moves_out", "population"]].sum(min_count=1)
    g["net_rate"] = (g.moves_in - g.moves_out) / g.population * 1000
    order = ["Tokyo area", "Osaka & Nagoya areas", "Rest of Japan"]

    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.axhline(0, color=ps.BASELINE, lw=1)
    for i, b in enumerate(order):
        s = g.loc[b].net_rate.dropna()
        s = s[s.index <= 2024]
        ax.plot(s.index, s, color=ps.SERIES[i])
        ax.text(s.index[-1] + 0.6, s.iloc[-1], b, color=ps.INK_2, fontsize=9, va="center")
    ax.set_xlim(1975, 2035)
    ax.set_title("Net migration between prefectures, by region group")
    ax.set_ylabel("Net moves in per 1,000 residents")
    mark_events(ax)
    ps.save(fig, "04_migration_blocs")

    tk = g.loc["Tokyo area"].net_rate
    summary["tokyo_area_net_migration_per_1000"] = {int(k): round(v, 2) for k, v in tk.dropna().items()
                                                   if k in (1987, 1994, 2007, 2019, 2021, 2024)}
    summary["tokyo_area_min_year_1985_2000"] = int(tk.loc[1985:2000].idxmin())


def heatmap(panel: pd.DataFrame, summary: dict) -> None:
    h = panel.pivot_table(index="pref_name", columns="period_label", values="growth")
    h = h.loc[h.mean(axis=1).sort_values().index]
    summary["prefs_declining_by_period"] = (panel.assign(dec=panel.growth < 0)
                                            .groupby("period_label").dec.sum().astype(int).to_dict())
    lim = np.nanmax(np.abs(h.values))
    fig, ax = plt.subplots(figsize=(7, 11))
    im = ax.imshow(h.values, cmap=ps.DIVERGING, vmin=-lim, vmax=lim, aspect="auto")
    ax.set_yticks(range(len(h)), h.index, fontsize=8)
    ax.set_xticks(range(h.shape[1]), h.columns, rotation=45, ha="right", fontsize=8)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, h.shape[1]), minor=True)
    ax.set_yticks(np.arange(-.5, len(h)), minor=True)
    ax.grid(which="minor", color=ps.SURFACE, lw=2)
    ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=ax, shrink=0.4, pad=0.02)
    cb.set_label("Population change over 5 years (%)", color=ps.INK_2)
    cb.outline.set_visible(False)
    ax.set_title("Population change by prefecture and period\n(red = decline, blue = growth; Fukushima 2010+ excluded)")
    ps.save(fig, "05_prefecture_growth_heatmap")


def decomposition(panel: pd.DataFrame) -> None:
    periods = sorted(panel.period_label.unique())
    fig, axes = plt.subplots(2, 4, figsize=(11, 5.6), sharex=True, sharey=True)
    lim = np.ceil(max(panel.natural.abs().max(), panel.social.abs().max()))
    for ax, per in zip(axes.flat, periods):
        d = panel[panel.period_label == per]
        ax.axhline(0, color=ps.BASELINE, lw=1)
        ax.axvline(0, color=ps.BASELINE, lw=1)
        ax.plot([-lim, lim], [lim, -lim], color=ps.GRID, lw=1, ls=(0, (2, 2)))
        ax.scatter(d.natural, d.social, s=16, color=ps.SERIES[0], edgecolor=ps.SURFACE, linewidth=1)
        for name in ("Tokyo", "Akita", "Okinawa"):
            r = d[d.pref_name == name]
            if len(r):
                ax.annotate(name, (r.natural.iloc[0], r.social.iloc[0]), xytext=(4, 3),
                            textcoords="offset points", fontsize=7, color=ps.INK_2)
        ax.set_title(per, fontsize=10, fontweight="normal")
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
    fig.supxlabel("Natural change (% over 5 years)", color=ps.INK_2, fontsize=10)
    fig.supylabel("Social change / net migration (%)", color=ps.INK_2, fontsize=10)
    fig.suptitle("Each prefecture's natural vs. social change; below the dashed line = shrinking",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    ps.save(fig, "06_natural_vs_social")


def municipalities(m: pd.DataFrame, summary: dict) -> None:
    s = m.groupby("period_label").agg(
        shrinking=("growth", lambda x: (x < 0).mean() * 100),
        fast=("growth", lambda x: (x < -10).mean() * 100),
        nat_neg=("natural", lambda x: (x < 0).mean() * 100),
        soc_neg=("social", lambda x: (x < 0).mean() * 100))
    summary["municipal_shares_pct"] = s.round(1).to_dict(orient="index")

    fig, ax = plt.subplots(figsize=(8, 3.8))
    cols = [("shrinking", "Population shrinking"), ("nat_neg", "More deaths than births"),
            ("fast", "Shrinking more than 10%")]
    for i, (c, lab) in enumerate(cols):
        ax.plot(range(len(s)), s[c], color=ps.SERIES[i], marker="o", markersize=8,
                markeredgecolor=ps.SURFACE, markeredgewidth=2)
        ax.text(len(s) - 1 + 0.12, s[c].iloc[-1], f"{lab} ({s[c].iloc[-1]:.0f}%)", va="center",
                fontsize=9, color=ps.INK_2)
    ax.set_xticks(range(len(s)), s.index)
    ax.set_xlim(-0.2, len(s) + 1.8)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of municipalities")
    ax.set_title("Share of the 1,741 municipalities that are shrinking")
    ps.save(fig, "07_municipal_shrinking_share")

    # Size matters: small municipalities shrink much faster.
    m = m.copy()
    m["size"] = pd.cut(m.pop_start, [0, 5e3, 2e4, 5e4, 2e5, np.inf],
                       labels=["<5k", "5–20k", "20–50k", "50–200k", "200k+"])
    t = m[m.period == 2015].groupby("size", observed=True)[["growth", "natural", "social"]].median()
    summary["municipal_median_2015_by_size"] = t.round(2).to_dict(orient="index")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = np.arange(len(t))
    w = 0.38
    for i, (c, lab) in enumerate([("natural", "Natural change"), ("social", "Social change")]):
        bars = ax.bar(x + (i - 0.5) * (w + 0.02), t[c], width=w, color=ps.SERIES[i], label=lab)
        for b, v in zip(bars, t[c]):
            ax.text(b.get_x() + b.get_width() / 2, v - 0.25 if v < 0 else v + 0.1, f"{v:.1f}",
                    ha="center", va="top" if v < 0 else "bottom", fontsize=8, color=ps.INK_2)
    ax.axhline(0, color=ps.BASELINE, lw=1)
    ax.set_xticks(x, t.index)
    ax.set_xlabel("Municipality population in 2015")
    ax.set_ylabel("Median change 2015–2020 (%)")
    ax.legend(loc="lower right")
    ax.set_title("Small municipalities lose people both ways")
    ps.save(fig, "08_municipal_change_by_size")


def correlations(panel: pd.DataFrame, summary: dict) -> None:
    feats = ["aging_rate", "young_women_share", "tfr", "unmarried_f_30_34_rate", "income_rel",
             "job_openings_ratio", "unemployment_rate", "did_share", "vacancy_rate", "land_price_rel",
             "univ_outflow_share", "hs_grads_jobs_other_pref", "univ_capacity_index", "doctors_per_100k",
             "fiscal_strength", "snow_days_5y", "log_population", "dist_metro_km"]
    c = panel[feats + ["natural", "social"]].corr(method="spearman").loc[feats, ["natural", "social"]]
    summary["spearman_with_targets"] = c.round(2).to_dict(orient="index")
    c = c.sort_values("social")
    fig, axes = plt.subplots(1, 2, figsize=(10, 6), sharey=True)
    for ax, col, color in zip(axes, ["natural", "social"], ps.SERIES[:2]):
        ax.barh(range(len(c)), c[col], color=color, height=0.7)
        ax.axvline(0, color=ps.BASELINE, lw=1)
        ax.set_xlim(-1, 1)
        ax.set_title(f"vs. {col} change", fontsize=10)
        ax.grid(axis="y", visible=False)
        for i, v in enumerate(c[col]):
            ax.text(v + (0.03 if v >= 0 else -0.03), i, f"{v:.2f}", va="center",
                    ha="left" if v >= 0 else "right", fontsize=7, color=ps.INK_2)
    axes[0].set_yticks(range(len(c)), c.index, fontsize=8)
    fig.suptitle("Rank correlation of start-of-period features with the next 5 years' change (prefectures)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    ps.save(fig, "09_feature_correlations")


def main() -> None:
    ps.apply()
    (ROOT / "reports").mkdir(exist_ok=True)
    y = pd.read_parquet(PROC / "pref_yearly.parquet")
    pref = pd.read_parquet(PROC / "pref_panel.parquet")
    muni = pd.read_parquet(PROC / "muni_panel.parquet")
    summary: dict = {}
    national(y, summary)
    peaks(y, summary)
    migration_blocs(y, summary)
    heatmap(pref, summary)
    decomposition(pref)
    municipalities(muni, summary)
    correlations(pref, summary)
    (ROOT / "reports" / "eda_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
