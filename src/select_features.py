"""Step 7: attribute (feature) selection.

Usage:
    python src/select_features.py

For each level (prefecture, municipality) and target (natural, social change):
  1. Period-demean features and target, so selection compares areas *within* the same
     period and isn't driven by the shared national trend.
  2. VIF on the standardized candidates (how much each one overlaps with the others).
  3. LassoCV with grouped CV (folds = whole areas, so an area never sits in both train and test).
  4. Stability selection: Lasso at the CV-chosen alpha on bootstrap resamples of whole areas;
     selection frequency per feature.
  5. Random-forest permutation importance, out-of-fold.
Then a rule picks the final set: stability >= 0.6, then among pairs correlated |r| > 0.8 keep
the more stable one, capped at 8 features.

Outputs: reports/feature_selection.md, reports/feature_selection_<level>.csv,
config/selected_features.json, figure 10.
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Lasso, LassoCV
from sklearn.model_selection import GroupKFold
from statsmodels.stats.outliers_influence import variance_inflation_factor

import features as F
import plotstyle as ps
from estat import ROOT

RNG = np.random.default_rng(42)
N_BOOT = 300
STABILITY_MIN = 0.6
CORR_MAX = 0.8
MAX_FEATURES = 8


def prep(df: pd.DataFrame, feats: list[str], target: str):
    d = df.dropna(subset=feats + [target]).reset_index(drop=True)
    X = F.demean_by(d, feats)
    y = F.demean_by(d, [target])[target]
    X = (X - X.mean()) / X.std()
    return d, X, y


def vif(X: pd.DataFrame) -> pd.Series:
    return pd.Series([variance_inflation_factor(X.values, i) for i in range(X.shape[1])], index=X.columns)


def run(df: pd.DataFrame, feats: list[str], target: str, level: str, n_splits: int = 5) -> pd.DataFrame:
    d, X, y = prep(df, feats, target)
    groups = d["area_code"].values
    cv = GroupKFold(n_splits=n_splits)

    lcv = LassoCV(cv=list(cv.split(X, y, groups)), alphas=60, max_iter=20000).fit(X, y)
    alpha = lcv.alpha_
    lasso_r2 = 1 - lcv.mse_path_.mean(axis=1).min() / y.var()

    areas = np.unique(groups)
    pos = {a: np.where(groups == a)[0] for a in areas}
    freq = np.zeros(len(feats))
    for _ in range(N_BOOT):
        idx = np.concatenate([pos[a] for a in RNG.choice(areas, size=len(areas), replace=True)])
        coef = Lasso(alpha=alpha, max_iter=20000).fit(X.iloc[idx], y.iloc[idx]).coef_
        freq += coef != 0
    freq /= N_BOOT

    imp = np.zeros(len(feats))
    oof_ss = 0.0
    for tr, te in cv.split(X, y, groups):
        rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=0)
        rf.fit(X.iloc[tr], y.iloc[tr])
        oof_ss += ((y.iloc[te] - rf.predict(X.iloc[te])) ** 2).sum()
        pi = permutation_importance(rf, X.iloc[te], y.iloc[te], n_repeats=5, random_state=0, n_jobs=-1)
        imp += pi.importances_mean / n_splits
    rf_r2 = 1 - oof_ss / ((y - y.mean()) ** 2).sum()

    res = pd.DataFrame({
        "feature": feats, "label": [F.LABELS.get(f, f) for f in feats],
        "lasso_coef": lcv.coef_, "stability": freq, "rf_importance": imp, "vif": vif(X).values,
        "spearman": [X[f].corr(y, method="spearman") for f in feats],
    })
    res["level"], res["target"], res["n_obs"] = level, target, len(d)
    res["lasso_cv_r2"], res["rf_cv_r2"] = lasso_r2, rf_r2
    res["selected"] = False
    # Selection rule.
    corr = X.corr().abs()
    chosen: list[str] = []
    for f in res.sort_values(["stability", "rf_importance"], ascending=False).feature:
        s = res.set_index("feature").loc[f, "stability"]
        if s < STABILITY_MIN or len(chosen) >= MAX_FEATURES:
            continue
        if all(corr.loc[f, c] <= CORR_MAX for c in chosen):
            chosen.append(f)
    res.loc[res.feature.isin(chosen), "selected"] = True
    print(f"[{level}/{target}] n={len(d)}  lasso CV R2={lasso_r2:.2f}  RF CV R2={rf_r2:.2f}  selected={chosen}")
    return res.sort_values("stability", ascending=False)


def figure(results: list[pd.DataFrame], name: str, title: str) -> None:
    fig, axes = plt.subplots(1, len(results), figsize=(5.2 * len(results), 0.32 * len(results[0]) + 1.6),
                             sharey=False)
    for ax, r in zip(np.atleast_1d(axes), results):
        r = r.sort_values("stability")
        colors = [ps.SERIES[0] if s else ps.BLUE_RAMP[1] for s in r.selected]
        ax.barh(range(len(r)), r.stability, color=colors, height=0.7)
        ax.axvline(STABILITY_MIN, color=ps.MUTED, lw=1, ls=(0, (3, 3)))
        ax.set_yticks(range(len(r)), r.label, fontsize=8)
        ax.set_xlim(0, 1.05)
        ax.grid(axis="y", visible=False)
        sign = np.sign(r.lasso_coef.where(r.lasso_coef != 0, r.spearman))
        for i, (v, sg) in enumerate(zip(r.stability, sign)):
            ax.text(v + 0.02, i, "+" if sg > 0 else "−", va="center", fontsize=9, color=ps.INK_2)
        t = r.target.iloc[0]
        ax.set_title(f"{t.capitalize()} change   (CV R²: Lasso {r.lasso_cv_r2.iloc[0]:.2f}, "
                     f"RF {r.rf_cv_r2.iloc[0]:.2f})", fontsize=10)
        ax.set_xlabel("Selection frequency over 300 bootstrap resamples")
    fig.suptitle(title + "\nDark = selected; sign = direction of effect; dashed = 0.6 threshold",
                 x=0.01, ha="left", fontweight="bold", fontsize=11)
    fig.tight_layout()
    ps.save(fig, name)


def main() -> None:
    ps.apply()
    pref, muni = F.load_pref(), F.load_muni()
    out: dict = {}
    tables = []

    # Prefecture, 1985-2015 starts (income starts 1985).
    pr = [run(pref, F.PREF_FEATURES, t, "pref") for t in F.TARGETS]
    figure(pr, "10_feature_stability_pref", "Feature selection, prefectures (1985–2020, within-period)")
    # Prefecture, post-2000 with the university-outflow variable.
    pr2 = [run(pref[pref.period >= 2000], F.PREF_FEATURES_POST2000, t, "pref_post2000") for t in F.TARGETS]
    # Municipality: core features (1995/2005-2020), and with vacancy + women (2005-2015 starts).
    mu = [run(muni, F.MUNI_FEATURES, t, "muni") for t in F.TARGETS]
    figure(mu, "11_feature_stability_muni", "Feature selection, municipalities (within-period)")
    mu2 = [run(muni[muni.period >= 2005], F.MUNI_FEATURES_EXTRA, t, "muni_extra") for t in F.TARGETS]

    for group in (pr, pr2, mu, mu2):
        for r in group:
            tables.append(r)
            out.setdefault(r.level.iloc[0], {})[r.target.iloc[0]] = r[r.selected].feature.tolist()

    allr = pd.concat(tables)
    for lv, g in allr.groupby("level"):
        g.round(3).to_csv(ROOT / "reports" / f"feature_selection_{lv}.csv", index=False)
    (ROOT / "config" / "selected_features.json").write_text(json.dumps(out, indent=1))

    lines = ["# Step 7: feature selection results", "",
             "Generated by `python src/select_features.py`. Method: see the module docstring. "
             "All features and targets are period-demeaned (compared within the same period).", ""]
    for lv, g in allr.groupby("level", sort=False):
        lines.append(f"## {lv}")
        for t, h in g.groupby("target"):
            lines.append(f"\n**{t}**: n = {h.n_obs.iloc[0]}, Lasso CV R² = {h.lasso_cv_r2.iloc[0]:.2f}, "
                         f"RF CV R² = {h.rf_cv_r2.iloc[0]:.2f}\n")
            lines.append("| Feature | Stability | Lasso coef | RF importance | VIF | Spearman | Selected |")
            lines.append("|---|---|---|---|---|---|---|")
            for r in h.itertuples():
                lines.append(f"| {r.label} | {r.stability:.2f} | {r.lasso_coef:+.3f} | {r.rf_importance:.3f} | "
                             f"{r.vif:.1f} | {r.spearman:+.2f} | {'✓' if r.selected else ''} |")
        lines.append("")
    (ROOT / "reports" / "feature_selection.md").write_text("\n".join(lines))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
