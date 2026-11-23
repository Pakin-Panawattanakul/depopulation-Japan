"""Step 8b: forecast population 5 and 10 years ahead, with honest out-of-time backtests.

Usage:
    python src/forecast.py

A forecast made at year t may only use information known at t:
  - features measured at t (start of period), plus the change over the previous period;
  - training rows whose outcome had already happened by t (period + horizon <= t).

Models:
  naive        the last period's change repeats
  ridge        linear model on standardized features (can extrapolate trends)
  gbm          histogram gradient boosting (non-linear; cannot extrapolate beyond training range)
  *_parts      predict natural and social change separately and add them up

Backtests: 5-year horizon tested on periods starting 2005, 2010, 2015; 10-year horizon on
2010 (-> 2020). Then every model is refit on all data to forecast 2020->2025 and 2020->2030.
The 2020->2025 forecast is checked against the official 2024 population estimates.

Outputs: reports/forecast.md, reports/forecast_pref.csv, reports/forecast_muni.csv,
reports/backtest_metrics.csv, figures 15-17.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import features as F
import plotstyle as ps
from estat import ROOT

PROC = ROOT / "data" / "processed"
PREF_X = ["aging_rate", "young_women_share", "tfr", "unmarried_f_30_34_rate", "income_rel",
          "job_openings_ratio", "unemployment_rate", "did_share", "vacancy_rate", "hs_grads_jobs_other_pref",
          "fiscal_strength", "snow_days_5y", "log_population", "log_dist_metro"]
MUNI_X = ["aging_rate", "income_rel", "unemployment_rate", "did_share", "log_population", "doctors_per_1k",
          "fiscal_strength", "log_dist_metro"]
LAGS = ["lag_growth", "lag_natural", "lag_social"]


def with_lags(panel: pd.DataFrame, future: pd.DataFrame) -> pd.DataFrame:
    d = pd.concat([panel, future], ignore_index=True).sort_values(["area_code", "period"])
    g = d.groupby("area_code")
    for c in ["growth", "natural", "social"]:
        prev = g[c].shift(1)
        same_gap = (d.period - g.period.shift(1)) == 5
        d[f"lag_{c}"] = prev.where(same_gap)
    # 10-year outcome: population at t+10 relative to t.
    nxt = g.pop_end.shift(-1).where((g.period.shift(-1) - d.period) == 5)
    d["growth10"] = (nxt / d.pop_start - 1) * 100
    return d.reset_index(drop=True)


def model(kind: str):
    if kind == "ridge":
        return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                             RidgeCV(alphas=np.logspace(-2, 3, 30)))
    return HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=15,
                                         min_samples_leaf=10, l2_regularization=1.0, random_state=0)


def predict(train: pd.DataFrame, test: pd.DataFrame, X: list[str], horizon: int) -> pd.DataFrame:
    """All model variants for one train/test split. Returns test rows with prediction columns."""
    out = test[["area_code", "period", "pop_start"]].copy()
    tgt = "growth" if horizon == 5 else "growth10"
    tr = train.dropna(subset=[tgt, "lag_growth"])
    if horizon == 5:
        out["naive"] = test.lag_growth
    else:  # repeat last 5-year rate twice (compounded)
        out["naive"] = ((1 + test.lag_growth / 100) ** 2 - 1) * 100
    for kind in ["ridge", "gbm"]:
        out[kind] = model(kind).fit(tr[X], tr[tgt]).predict(test[X])
        if horizon == 5:
            parts = sum(model(kind).fit(tr[X], tr[c]).predict(test[X]) for c in ["natural", "social"])
            out[f"{kind}_parts"] = parts
    return out


def metrics(pred: pd.DataFrame, actual: pd.Series, pop_start: pd.Series, models: list[str]) -> list[dict]:
    rows = []
    for m in models:
        err = pred[m] - actual
        pop_err = pop_start * err / 100
        rows.append({"model": m, "mae_pp": err.abs().mean(), "rmse_pp": np.sqrt((err ** 2).mean()),
                     "bias_pp": err.mean(), "total_pop_error_pct": pop_err.sum() / pop_start.sum() * 100})
    return rows


def backtest(d: pd.DataFrame, X: list[str], level: str, tests5: list[int], tests10: list[int]):
    rows, preds = [], []
    for horizon, tests in [(5, tests5), (10, tests10)]:
        tgt = "growth" if horizon == 5 else "growth10"
        for t in tests:
            train = d[d.period + horizon <= t]
            test = d[(d.period == t)].dropna(subset=[tgt, "lag_growth"])
            p = predict(train, test, X, horizon)
            models = [c for c in p.columns if c not in ("area_code", "period", "pop_start")]
            for r in metrics(p, test[tgt].values, test.pop_start.values, models):
                rows.append({"level": level, "horizon": horizon, "test_period": f"{t}-{t + horizon}",
                             "n_test": len(test), **r})
            p["actual"] = test[tgt].values
            p["horizon"] = horizon
            preds.append(p)
    return pd.DataFrame(rows), pd.concat(preds)


def residual_band(preds: pd.DataFrame, model_name: str, horizon: int) -> tuple[float, float]:
    """80% prediction interval: +/- the 80th percentile of absolute backtest errors.

    Symmetric on purpose. There are only 1-3 backtests per horizon and their bias flips sign
    between periods (the 10-year model over-predicted decline in 2010-2020, while the
    2020-2024 live check shows under-prediction), so an asymmetric band would overfit one period.
    """
    p = preds[preds.horizon == horizon]
    q = float((p["actual"] - p[model_name]).abs().quantile(0.8))
    return -q, q


def main() -> None:
    ps.apply()
    pref = with_lags(F.load_pref(), F.add_transforms(pd.read_parquet(PROC / "pref_start_2020.parquet")))
    pref = pref[pref.period >= 1985]
    muni = with_lags(F.load_muni(), F.add_transforms(pd.read_parquet(PROC / "muni_start_2020.parquet")))

    mp, pp = backtest(pref, PREF_X + LAGS, "pref", [2005, 2010, 2015], [2010])
    mm, pm = backtest(muni, MUNI_X + LAGS, "muni", [2010, 2015], [2010])
    met = pd.concat([mp, mm])
    met.to_csv(ROOT / "reports" / "backtest_metrics.csv", index=False)

    # Pick the best model per level and horizon by mean MAE across backtests.
    best = (met.groupby(["level", "horizon", "model"]).mae_pp.mean().reset_index()
            .sort_values("mae_pp").groupby(["level", "horizon"]).head(1).set_index(["level", "horizon"]).model)
    print(met.round(2).to_string(index=False))
    print("best:", best.to_dict())

    # Final forecasts from 2020.
    out = {}
    for level, d, X, preds in [("pref", pref, PREF_X + LAGS, pp), ("muni", muni, MUNI_X + LAGS, pm)]:
        future = d[d.period == 2020]
        p5 = predict(d[d.period + 5 <= 2020], future, X, 5)
        p10 = predict(d[d.period + 10 <= 2020], future, X, 10)
        m5, m10 = best[(level, 5)], best[(level, 10)]
        lo5, hi5 = residual_band(preds, m5, 5)
        lo10, hi10 = residual_band(preds, m10, 10)
        f = future[["area_code", "pop_start"]].copy()
        if "pref_name" in future:
            f["name"] = future.pref_name.values
        if "area_name" in future and level == "muni":
            f["name"] = future.area_name.values
        f["growth_2025"], f["growth_2025_lo"], f["growth_2025_hi"] = p5[m5].values, p5[m5].values + lo5, p5[m5].values + hi5
        f["growth_2030"], f["growth_2030_lo"], f["growth_2030_hi"] = p10[m10].values, p10[m10].values + lo10, p10[m10].values + hi10
        f["pop_2025"] = f.pop_start * (1 + f.growth_2025 / 100)
        f["pop_2030"] = f.pop_start * (1 + f.growth_2030 / 100)
        f["model_5y"], f["model_10y"] = m5, m10
        out[level] = f

    # Live check: 2020 -> 2024 official estimates (4 of the 5 forecast years).
    y = pd.read_parquet(PROC / "pref_yearly.parquet")
    p24 = y[y.year == 2024].set_index("area_code").population
    fp = out["pref"]
    fp["actual_2024"] = fp.area_code.map(p24)
    fp["actual_growth_2020_2024"] = (fp.actual_2024 / fp.pop_start - 1) * 100
    fp["pred_growth_2020_2024"] = ((1 + fp.growth_2025 / 100) ** 0.8 - 1) * 100  # 4/5 of the period
    live_mae = (fp.pred_growth_2020_2024 - fp.actual_growth_2020_2024).abs().mean()
    live_corr = fp.pred_growth_2020_2024.corr(fp.actual_growth_2020_2024)
    fp.round(3).to_csv(ROOT / "reports" / "forecast_pref.csv", index=False)
    out["muni"].round(3).to_csv(ROOT / "reports" / "forecast_muni.csv", index=False)

    figures(met, pp, fp, best)

    # Report.
    L = ["# Step 8b: forecasting", "", "Generated by `python src/forecast.py`; see the module docstring for the method.", "",
         "## Backtests (out-of-time)", "",
         "MAE = mean absolute error of the predicted 5- or 10-year population change, in percentage points. "
         "Bias = mean error (negative = predicted too much decline). "
         "Total error = error in the summed population of all test areas.", ""]
    for (lv, h), g in met.groupby(["level", "horizon"], sort=False):
        L += [f"### {'Prefectures' if lv == 'pref' else 'Municipalities'}, {h}-year horizon", "",
              "| Model | " + " | ".join(f"MAE {t}" for t in g.test_period.unique()) + " | Mean MAE | Mean bias |",
              "|---|" + "---|" * (g.test_period.nunique() + 2)]
        for m, gm in g.groupby("model"):
            cells = " | ".join(f"{v:.2f}" for v in gm.mae_pp)
            mark = " **(best)**" if best[(lv, h)] == m else ""
            L.append(f"| {m}{mark} | {cells} | {gm.mae_pp.mean():.2f} | {gm.bias_pp.mean():+.2f} |")
        L.append("")
    nat = fp.pop_start.sum()
    L += ["## Forecast from 2020 (prefectures, excluding Fukushima)", "",
          f"Total for the 46 prefectures: {nat / 1e6:.2f}M (2020) → {fp.pop_2025.sum() / 1e6:.2f}M (2025) → "
          f"{fp.pop_2030.sum() / 1e6:.2f}M (2030).", "",
          f"**Live check against 2024 official estimates:** MAE {live_mae:.2f} pp over 2020–2024, "
          f"correlation {live_corr:.2f} between predicted and actual change.", "",
          "| Prefecture | 2020 | 2025 forecast (80% interval) | 2030 forecast (80% interval) | Actual 2020→24 | Predicted 2020→24 |",
          "|---|---|---|---|---|---|"]
    for r in fp.sort_values("growth_2030").itertuples():
        L.append(f"| {r.name} | {r.pop_start / 1e3:,.0f}k | {r.growth_2025:+.1f}% [{r.growth_2025_lo:+.1f}, {r.growth_2025_hi:+.1f}] | "
                 f"{r.growth_2030:+.1f}% [{r.growth_2030_lo:+.1f}, {r.growth_2030_hi:+.1f}] | "
                 f"{r.actual_growth_2020_2024:+.1f}% | {r.pred_growth_2020_2024:+.1f}% |")
    fm = out["muni"]
    L += ["", "## Forecast from 2020 (municipalities)", "",
          f"{len(fm)} municipalities. Predicted to shrink 2020→2025: {(fm.growth_2025 < 0).mean():.0%}; "
          f"shrink by more than 10% by 2030: {(fm.growth_2030 < -10).mean():.0%}. Full table: `reports/forecast_muni.csv`.", ""]
    (ROOT / "reports" / "forecast.md").write_text("\n".join(L))
    print("\n".join(L[-60:]))


def figures(met: pd.DataFrame, pp: pd.DataFrame, fp: pd.DataFrame, best) -> None:
    # 15: backtest MAE by model (5-year, both levels).
    g = met[met.horizon == 5].groupby(["level", "model"]).mae_pp.mean().unstack(0)
    order = ["naive", "ridge", "ridge_parts", "gbm", "gbm_parts"]
    g = g.loc[order]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, lv, title in zip(axes, ["pref", "muni"], ["Prefectures", "Municipalities"]):
        v = g[lv]
        colors = [ps.SERIES[0] if m == best[(lv, 5)] else ps.BLUE_RAMP[1] for m in v.index]
        ax.barh(range(len(v)), v, color=colors, height=0.65)
        for i, x in enumerate(v):
            ax.text(x + v.max() * 0.02, i, f"{x:.2f}", va="center", fontsize=8, color=ps.INK_2)
        ax.set_yticks(range(len(v)), v.index)
        ax.set_xlim(0, v.max() * 1.2)
        ax.grid(axis="y", visible=False)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Mean absolute error (pp)")
        ax.invert_yaxis()
    fig.suptitle("5-year forecast error in out-of-time backtests (dark = best)", x=0.01, ha="left",
                 fontweight="bold", fontsize=11)
    fig.tight_layout()
    ps.save(fig, "15_backtest_errors")

    # 16: predicted vs actual, prefectures, test 2015-2020, best 5-year model.
    m = best[("pref", 5)]
    p = pp[(pp.horizon == 5) & (pp.period == 2015)]
    fig, ax = plt.subplots(figsize=(5.2, 5))
    lim = [min(p.actual.min(), p[m].min()) - 0.5, max(p.actual.max(), p[m].max()) + 0.5]
    ax.plot(lim, lim, color=ps.BASELINE, lw=1)
    ax.scatter(p[m], p.actual, s=28, color=ps.SERIES[0], edgecolor=ps.SURFACE, linewidth=1.5, zorder=3)
    names = F.load_pref().drop_duplicates("area_code").set_index("area_code").pref_name
    for r in p.itertuples():
        if abs(getattr(r, m) - r.actual) > 0.8 or r.actual > 2 or r.actual < -5.5:
            ax.annotate(names[r.area_code], (getattr(r, m), r.actual), xytext=(4, 2), textcoords="offset points",
                        fontsize=7, color=ps.INK_2)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel(f"Predicted change 2015–2020 (%), model: {m}")
    ax.set_ylabel("Actual change 2015–2020 (%)")
    ax.set_title("Backtest: forecast made in 2015 vs. what happened")
    ps.save(fig, "16_backtest_pref_2015")

    # 17: 2030 forecast per prefecture with 80% interval, plus 2020-24 actual (scaled) as check.
    f = fp.sort_values("growth_2030")
    fig, ax = plt.subplots(figsize=(7.5, 10))
    y = np.arange(len(f))
    ax.hlines(y, f.growth_2030_lo, f.growth_2030_hi, color=ps.BLUE_RAMP[1], lw=4)
    ax.scatter(f.growth_2030, y, color=ps.SERIES[0], s=30, zorder=3, edgecolor=ps.SURFACE, linewidth=1.5,
               label="Forecast 2020→2030 (80% interval)")
    ax.scatter(f.growth_2025, y, color=ps.SERIES[1], s=22, zorder=3, marker="D", edgecolor=ps.SURFACE,
               linewidth=1, label="Forecast 2020→2025")
    ax.axvline(0, color=ps.BASELINE, lw=1)
    ax.set_yticks(y, f.name, fontsize=8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Population change from 2020 (%)")
    ax.set_title("Forecast population change by prefecture", pad=28)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.035), ncol=2, fontsize=8)
    ps.save(fig, "17_forecast_pref")


if __name__ == "__main__":
    main()
