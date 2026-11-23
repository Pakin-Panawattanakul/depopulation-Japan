"""Step 9: do the most important factors change over time?

Usage:
    python src/time_varying.py

For each 5-year period separately, regress natural and social change on one fixed set of
features (z-scored within the period, so coefficients compare across periods):
  - Shapley R² decomposition (dominance analysis): each feature's share of the explained
    variance, averaged over all orders of entry. Robust to correlated features, which matters
    with 47 prefectures.
  - Standardized coefficients with 95% bootstrap intervals (resampling areas).
  - An F-test of "coefficients are the same in every period": pooled model with
    feature x period interactions vs. without (both with period fixed effects).

Outputs: reports/time_varying.md, reports/time_varying_<level>.csv, figures 18-20.
"""

from __future__ import annotations

from itertools import combinations
from math import factorial

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

import features as F
import plotstyle as ps
from estat import ROOT

RNG = np.random.default_rng(7)
N_BOOT = 500
SETS = {
    ("pref", "social"): ["income_rel", "job_openings_ratio", "unemployment_rate", "aging_rate",
                         "log_dist_metro", "snow_days_5y"],
    ("pref", "natural"): ["aging_rate", "tfr", "unmarried_f_30_34_rate", "income_rel", "vacancy_rate"],
    ("muni", "social"): ["aging_rate", "fiscal_strength", "income_rel", "log_population", "did_share",
                         "unemployment_rate"],
    ("muni", "natural"): ["aging_rate", "did_share", "income_rel", "log_population", "unemployment_rate"],
}
# README framing: roughly 30, 20, 10 years before the latest period, and now.
ERA = {1985: "~30 yrs ago", 1995: "~20 yrs ago", 2005: "~10 yrs ago", 2015: "now"}


def r2(X: np.ndarray, y: np.ndarray) -> float:
    if X.shape[1] == 0:
        return 0.0
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    return 1 - resid @ resid / ((y - y.mean()) @ (y - y.mean()))


def shapley_r2(X: pd.DataFrame, y: pd.Series) -> pd.Series:
    """Exact Shapley decomposition of R² (fine for <= 8 features)."""
    cols = list(X.columns)
    k = len(cols)
    Xv, yv = X.values, y.values
    cache: dict[frozenset, float] = {}

    def val(s: frozenset) -> float:
        if s not in cache:
            cache[s] = r2(Xv[:, sorted(cols.index(c) for c in s)], yv)
        return cache[s]

    out = {}
    for c in cols:
        others = [o for o in cols if o != c]
        tot = 0.0
        for m in range(k):
            w = factorial(m) * factorial(k - m - 1) / factorial(k)
            for S in combinations(others, m):
                s = frozenset(S)
                tot += w * (val(s | {c}) - val(s))
        out[c] = tot
    return pd.Series(out)


def per_period(df: pd.DataFrame, level: str, target: str) -> pd.DataFrame:
    feats = SETS[(level, target)]
    rows = []
    for per, g in df.dropna(subset=feats + [target]).groupby("period"):
        X = (g[feats] - g[feats].mean()) / g[feats].std()
        y = g[target]
        A = np.column_stack([np.ones(len(y)), X.values])
        beta = np.linalg.lstsq(A, y.values, rcond=None)[0][1:]
        boots = []
        n = len(g)
        for _ in range(N_BOOT):
            i = RNG.integers(0, n, n)
            Xb = X.values[i]
            Xb = (Xb - Xb.mean(0)) / Xb.std(0, ddof=1)
            boots.append(np.linalg.lstsq(np.column_stack([np.ones(n), Xb]), y.values[i], rcond=None)[0][1:])
        lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
        sh = shapley_r2(X, y)
        total = r2(X.values, y.values)
        for j, f in enumerate(feats):
            rows.append({"level": level, "target": target, "period": per, "feature": f,
                         "label": F.LABELS.get(f, f), "coef": beta[j], "lo": lo[j], "hi": hi[j],
                         "shapley_r2": sh[f], "share_of_r2": sh[f] / total, "r2": total, "n": n})
    return pd.DataFrame(rows)


def stability_test(df: pd.DataFrame, level: str, target: str) -> dict:
    feats = SETS[(level, target)]
    d = df.dropna(subset=feats + [target]).copy()
    for f in feats:  # standardize within period, as in the per-period fits
        d[f] = d.groupby("period")[f].transform(lambda s: (s - s.mean()) / s.std())
    base = smf.ols(f"{target} ~ C(period) + " + " + ".join(feats), data=d).fit()
    full = smf.ols(f"{target} ~ C(period) * (" + " + ".join(feats) + ")", data=d).fit()
    a = anova_lm(base, full)
    return {"F": float(a.F.iloc[1]), "p": float(a["Pr(>F)"].iloc[1]), "df": int(a.df_diff.iloc[1])}


def plot_shares(res: pd.DataFrame, name: str, title: str) -> None:
    targets = [t for t in F.TARGETS if t in set(res.target)]
    # Colour follows the feature: features in both panels get the same slot in each, and are
    # stacked first; panel-specific features take the remaining slots.
    per_target = {t: list(dict.fromkeys(res[res.target == t].feature)) for t in targets}
    shared = [f for f in per_target[targets[0]] if all(f in per_target[t] for t in targets)]
    fig, axes = plt.subplots(1, len(targets), figsize=(5.4 * len(targets), 4.6))
    for ax, t in zip(np.atleast_1d(axes), targets):
        g = res[res.target == t]
        feats = shared + [f for f in per_target[t] if f not in shared]
        piv = g.pivot(index="period", columns="feature", values="shapley_r2")[feats]
        x = np.arange(len(piv))
        bottom = np.zeros(len(piv))
        for k, f in enumerate(feats):
            v = piv[f].clip(lower=0).values
            ax.bar(x, v, bottom=bottom, color=ps.SERIES[k], width=0.7, edgecolor=ps.SURFACE, linewidth=2,
                   label=F.LABELS.get(f, f))
            for i in range(len(v)):
                if v[i] > 0.09:
                    ax.text(x[i], bottom[i] + v[i] / 2, f"{v[i]:.2f}", ha="center", va="center", fontsize=7,
                            color=ps.INK if ps.SERIES[k] == "#eda100" else "#ffffff")
            bottom += v
        ax.set_xticks(x, [f"{p}–{p + 5}" for p in piv.index], rotation=45, ha="right", fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_ylabel("R² explained (Shapley share per feature)")
        ax.set_title(f"{t.capitalize()} change", fontsize=10)
        ax.grid(axis="x", visible=False)
        ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=11)
    fig.tight_layout()
    ps.save(fig, name)


def plot_coefs(res: pd.DataFrame, name: str, title: str) -> None:
    feats = list(dict.fromkeys(res.feature))
    ncol = 3
    nrow = int(np.ceil(len(feats) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(10, 2.6 * nrow), sharey=True)
    for ax, f in zip(axes.flat, feats):
        g = res[res.feature == f].sort_values("period")
        x = g.period + 2.5
        ax.fill_between(x, g.lo, g.hi, color=ps.BLUE_RAMP[0], lw=0)
        ax.plot(x, g.coef, color=ps.SERIES[0], marker="o", markersize=6, markeredgecolor=ps.SURFACE,
                markeredgewidth=1.5)
        ax.axhline(0, color=ps.BASELINE, lw=1)
        ax.set_title(F.LABELS.get(f, f), fontsize=9, fontweight="normal")
        ax.tick_params(labelsize=8)
    for ax in list(axes.flat)[len(feats):]:
        ax.set_visible(False)
    fig.supylabel("Effect of +1 SD (pp of 5-yr change)", fontsize=9, color=ps.INK_2)
    fig.suptitle(title + " (95% bootstrap band; x = period midpoint)", x=0.01, ha="left",
                 fontweight="bold", fontsize=11)
    fig.tight_layout()
    ps.save(fig, name)


def main() -> None:
    ps.apply()
    pref = F.load_pref()
    pref = pref[pref.period >= 1985]
    muni = F.load_muni()
    allres, tests = [], []
    for (level, target), _ in SETS.items():
        df = pref if level == "pref" else muni
        r = per_period(df, level, target)
        allres.append(r)
        tests.append({"level": level, "target": target, **stability_test(df, level, target)})
    res = pd.concat(allres)
    for lv, g in res.groupby("level"):
        g.round(4).to_csv(ROOT / "reports" / f"time_varying_{lv}.csv", index=False)
    tests = pd.DataFrame(tests)

    plot_shares(res[res.level == "pref"], "18_shapley_by_period_pref",
                "Which factors explain prefecture differences, period by period?")
    plot_coefs(res[(res.level == "pref") & (res.target == "social")], "19_coef_paths_pref_social",
               "Effect on prefecture social change (net migration) over time")
    plot_shares(res[res.level == "muni"], "20_shapley_by_period_muni",
                "Which factors explain municipal differences, period by period?")

    L = ["# Step 9: do the main factors change over time?", "",
         "Generated by `python src/time_varying.py`; method in the module docstring.", "",
         "## Are the coefficients the same in every period? (F-test, interactions vs. none)", "",
         "| Level | Target | F | df | p | Verdict |", "|---|---|---|---|---|---|"]
    for t in tests.itertuples():
        verdict = "factors **change** over time" if t.p < 0.05 else "no significant change"
        L.append(f"| {t.level} | {t.target} | {t.F:.2f} | {t.df} | {t.p:.4f} | {verdict} |")
    L.append("")
    for (lv, tg), g in res.groupby(["level", "target"], sort=False):
        L += [f"## {'Prefectures' if lv == 'pref' else 'Municipalities'}: {tg} change", "",
              "Shapley share of R² by period (bold = largest share that period); last row = total R².", ""]
        piv = g.pivot(index="label", columns="period", values="share_of_r2")
        coef = g.pivot(index="label", columns="period", values="coef")
        L.append("| Feature | " + " | ".join(f"{p}–{p + 5}" + (f" ({ERA[p]})" if p in ERA else "") for p in piv.columns) + " |")
        L.append("|---|" + "---|" * len(piv.columns))
        top = piv.idxmax()
        for lab in piv.index:
            cells = []
            for p in piv.columns:
                s = f"{piv.loc[lab, p]:.0%} ({coef.loc[lab, p]:+.2f})"
                cells.append(f"**{s}**" if top[p] == lab else s)
            L.append(f"| {lab} | " + " | ".join(cells) + " |")
        r2s = g.groupby("period").r2.first()
        L.append("| *Total R²* | " + " | ".join(f"{v:.2f}" for v in r2s) + " |")
        L += ["", "Cells: share of explained variance (standardized coefficient in pp per SD).", ""]
    (ROOT / "reports" / "time_varying.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
