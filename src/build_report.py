"""Step 10: assemble the shareable report page from the pipeline outputs.

Usage:
    python src/build_report.py      # -> reports/site/index.html

Interactive charts are drawn in the browser from data embedded in the page; denser
multi-panel figures are embedded as the PNGs from reports/figures/.
"""

from __future__ import annotations

import base64
import json

import pandas as pd

import geo
from estat import ROOT

REP = ROOT / "reports"
PROC = ROOT / "data" / "processed"
TEMPLATE = ROOT / "src" / "report_template.html"


def img(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((REP / "figures" / f"{name}.png").read_bytes()).decode()


def data() -> dict:
    y = pd.read_parquet(PROC / "pref_yearly.parquet")
    p = y[y.area_code != "00000"].copy()
    bloc = {**{c: "Tokyo area" for c in geo.TOKYO_AREA},
            **{c: "Osaka & Nagoya areas" for c in ["21", "23", "24", "26", "27", "28", "29"]}}
    p["bloc"] = p.pref.map(bloc).fillna("Rest of Japan")
    g = p.groupby(["bloc", "year"])[["moves_in", "moves_out", "population"]].sum(min_count=1)
    g["rate"] = (g.moves_in - g.moves_out) / g.population * 1000
    migration = [{"name": b, "points": [[int(yr), round(v, 2)] for yr, v in g.loc[b].rate.dropna().items() if yr <= 2024]}
                 for b in ["Tokyo area", "Osaka & Nagoya areas", "Rest of Japan"]]

    peaks = pd.read_csv(REP / "prefecture_peaks.csv")
    peaks = [{"name": r.pref_name, "region": r.region, "peak": int(r.peak_year),
              "since": round(r.change_since_peak_pct, 1), "growing": bool(r.still_growing)}
             for r in peaks.sort_values(["peak_year", "pref_name"]).itertuples()]

    fc = pd.read_csv(REP / "forecast_pref.csv")
    forecast = [{"name": r.name, "pop2020": int(r.pop_start), "g25": round(r.growth_2025, 2),
                 "g30": round(r.growth_2030, 2), "lo30": round(r.growth_2030_lo, 2), "hi30": round(r.growth_2030_hi, 2),
                 "lo25": round(r.growth_2025_lo, 2), "hi25": round(r.growth_2025_hi, 2),
                 "pop2030": int(r.pop_2030), "act24": round(r.actual_growth_2020_2024, 2),
                 "pred24": round(r.pred_growth_2020_2024, 2)}
                for r in fc.sort_values("growth_2030").itertuples()]

    tv = pd.read_csv(REP / "time_varying_pref.csv")
    shap = {}
    for t, gt in tv.groupby("target"):
        feats = list(dict.fromkeys(gt.feature))
        shap[t] = {"periods": [f"{p}–{p + 5}" for p in sorted(gt.period.unique())],
                   "r2": [round(v, 3) for v in gt.groupby("period").r2.first()],
                   "series": [{"name": gt[gt.feature == f].label.iloc[0],
                               "values": [round(max(v, 0), 3) for v in gt[gt.feature == f].sort_values("period").shapley_r2],
                               "coefs": [round(v, 2) for v in gt[gt.feature == f].sort_values("period").coef]}
                              for f in feats]}

    co = pd.read_csv(REP / "coefficients.csv")
    coefs = {}
    for (lv, t), gc in co.groupby(["level", "target"]):
        coefs[f"{lv}_{t}"] = [{"spec": s, "rows": [{"label": r.label, "coef": round(r.coef, 3), "lo": round(r.lo, 3),
                                                     "hi": round(r.hi, 3), "p": round(r.p, 4)} for r in gs.itertuples()]}
                               for s, gs in gc.groupby("spec", sort=False)]

    eda = json.loads((REP / "eda_summary.json").read_text())
    met = pd.read_csv(REP / "backtest_metrics.csv")
    best5 = met[(met.level == "pref") & (met.horizon == 5)].groupby("model").mae_pp.mean()
    return {"migration": migration, "peaks": peaks, "forecast": forecast, "shapley": shap, "coefs": coefs,
            "facts": {"peak_year": eda["national_peak_year"], "peak_pop": eda["national_peak_population"],
                      "first_nat_dec": eda["national_first_natural_decrease_year"],
                      "prefs_declining_now": eda["prefs_declining_by_period"]["2015-2020"],
                      "muni_shrinking": eda["municipal_shares_pct"]["2015-2020"]["shrinking"],
                      "pop2020": int(fc.pop_start.sum()), "pop2030": int(fc.pop_2030.sum()),
                      "mae_best": round(best5.min(), 2), "mae_naive": round(best5["naive"], 2)}}


def main() -> None:
    html = TEMPLATE.read_text()
    html = html.replace("/*__DATA__*/null", json.dumps(data(), ensure_ascii=False))
    for name in ["05_prefecture_growth_heatmap", "06_natural_vs_social", "07_municipal_shrinking_share",
                 "08_municipal_change_by_size", "14_anova_variance_shares", "16_backtest_pref_2015",
                 "20_shapley_by_period_muni", "13_coefficients_muni"]:
        html = html.replace(f"__IMG_{name}__", img(name))
    out = REP / "site" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
