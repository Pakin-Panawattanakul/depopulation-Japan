"""Step 8a: explanatory models ("what contributes most") and ANOVA.

Usage:
    python src/models.py

Regressions use the features chosen in step 7 (config/selected_features.json), z-scored so
coefficients are comparable: "+1 standard deviation of X -> +b percentage points of 5-year
change". Standard errors are clustered by area (repeated observations of one area are not
independent).

  Prefecture, spec A: period fixed effects. Compares prefectures within the same period.
  Prefecture, spec B: period + prefecture fixed effects. Uses only changes *within* a
                      prefecture over time (does a prefecture lose more people when its own
                      job market weakens?). Slow-moving variables lose power here.
  Municipality:       period + prefecture fixed effects (compares municipalities within the
                      same prefecture and period). Distance to metro is dropped here: it is a
                      prefecture-level value, so the prefecture fixed effects absorb it.
ANOVA: how much variance in change is explained by region, period, and (municipal) size class.

Outputs: reports/models_explanatory.md, reports/coefficients.csv, figures 12-14.
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd

import features as F
import plotstyle as ps
from estat import ROOT

SEL = json.loads((ROOT / "config" / "selected_features.json").read_text())


def fit(df: pd.DataFrame, target: str, feats: list[str], fe: list[str], cluster: str, extra: list[str] = ()):
    d = df.dropna(subset=feats + [target]).copy()
    for f in feats:
        d[f] = (d[f] - d[f].mean()) / d[f].std()
    rhs = " + ".join(list(feats) + list(extra) + [f"C({x})" for x in fe])
    m = smf.ols(f"{target} ~ {rhs}", data=d).fit(cov_type="cluster", cov_kwds={"groups": d[cluster]})
    ci = m.conf_int()
    out = pd.DataFrame({"coef": m.params, "lo": ci[0], "hi": ci[1], "p": m.pvalues}).loc[list(feats) + list(extra)]
    out["feature"] = out.index
    out["label"] = [F.LABELS.get(f, f) for f in out.index]
    # Within R2: share of variance left after the fixed effects that the features explain.
    base = smf.ols(f"{target} ~ " + " + ".join(f"C({x})" for x in fe), data=d).fit()
    within = 1 - m.ssr / base.ssr
    return out.reset_index(drop=True), {"n": int(m.nobs), "r2": m.rsquared, "within_r2": within}


def coef_plot(blocks: list[tuple[str, pd.DataFrame]], title: str, name: str) -> None:
    """blocks: (series name, coefficient table); up to 2 series per panel, one panel per target."""
    targets = sorted({t for t, _ in [(b[1].target.iloc[0], 0) for b in blocks]}, key=F.TARGETS.index)
    fig, axes = plt.subplots(1, len(targets), figsize=(5.6 * len(targets), 4.8), sharey=False)
    for ax, t in zip(np.atleast_1d(axes), targets):
        bs = [(n, b) for n, b in blocks if b.target.iloc[0] == t]
        feats = list(dict.fromkeys(f for _, b in bs for f in b.feature))
        feats = sorted(feats, key=lambda f: bs[0][1].set_index("feature").coef.get(f, 0))
        y = {f: i for i, f in enumerate(feats)}
        off = np.linspace(-0.16, 0.16, len(bs)) if len(bs) > 1 else [0]
        for k, ((nm, b), o) in enumerate(zip(bs, off)):
            yy = [y[f] + o for f in b.feature]
            ax.hlines(yy, b.lo, b.hi, color=ps.SERIES[k], lw=2)
            ax.scatter(b.coef, yy, color=ps.SERIES[k], s=40, zorder=3, edgecolor=ps.SURFACE, linewidth=2,
                       label=nm)
        ax.axvline(0, color=ps.BASELINE, lw=1)
        ax.set_yticks(range(len(feats)), [F.LABELS.get(f, f) for f in feats], fontsize=8)
        ax.grid(axis="y", visible=False)
        ax.set_title(f"{t.capitalize()} change", fontsize=10)
        ax.set_xlabel("Effect of +1 SD on 5-year change (pp), 95% CI")
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=11)
    fig.tight_layout()
    handles, labels = np.atleast_1d(axes)[0].get_legend_handles_labels()
    if len(handles) > 1:
        fig.subplots_adjust(top=0.82)
        fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.93), ncol=len(handles), fontsize=9)
    ps.save(fig, name)


def anova(pref: pd.DataFrame, muni: pd.DataFrame, lines: list[str]) -> None:
    rows = []
    for t in ["growth", *F.TARGETS]:
        m = smf.ols(f"{t} ~ C(region) + C(period_label) + C(region):C(period_label)", data=pref).fit()
        a = anova_lm(m, typ=2)
        a["eta_sq"] = a.sum_sq / a.sum_sq.sum()
        for term, r in a.iterrows():
            rows.append({"level": "pref", "target": t, "term": term, "F": r.F, "p": r["PR(>F)"], "eta_sq": r.eta_sq})
    mu = muni.copy()
    mu["size"] = pd.cut(mu.pop_start, [0, 5e3, 2e4, 5e4, 2e5, np.inf],
                        labels=["<5k", "5-20k", "20-50k", "50-200k", "200k+"]).astype(str)
    for t in ["growth", *F.TARGETS]:
        m = smf.ols(f"{t} ~ C(size) + C(region) + C(period_label)", data=mu).fit()
        a = anova_lm(m, typ=2)
        a["eta_sq"] = a.sum_sq / a.sum_sq.sum()
        for term, r in a.iterrows():
            rows.append({"level": "muni", "target": t, "term": term, "F": r.F, "p": r["PR(>F)"], "eta_sq": r.eta_sq})
    an = pd.DataFrame(rows)
    an.to_csv(ROOT / "reports" / "anova.csv", index=False)

    nice = {"C(region)": "Region", "C(period_label)": "Period", "C(region):C(period_label)": "Region × period",
            "C(size)": "Size class", "Residual": "Unexplained"}
    lines += ["## ANOVA: how much of the variation is due to region, period, size?", "",
              "Share of total variance (η², Type II sums of squares). All listed terms p < 0.001 unless noted.", ""]
    for lv, g in an.groupby("level", sort=False):
        piv = g.pivot(index="term", columns="target", values="eta_sq")[["growth", "natural", "social"]]
        pv = g.pivot(index="term", columns="target", values="p")
        lines += [f"**{'Prefectures' if lv == 'pref' else 'Municipalities'}**", "",
                  "| Term | Total growth | Natural | Social |", "|---|---|---|---|"]
        for term in piv.index:
            cells = []
            for t in ["growth", "natural", "social"]:
                p = pv.loc[term, t]
                star = "" if term == "Residual" or p < 0.001 else f" (p={p:.2f})"
                cells.append(f"{piv.loc[term, t]:.2f}{star}")
            lines.append(f"| {nice.get(term, term)} | " + " | ".join(cells) + " |")
        lines.append("")

    # Figure 14: stacked eta^2 per target, prefectures and municipalities.
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, (lv, g) in zip(axes, an.groupby("level", sort=False)):
        terms = [t for t in nice if t in set(g.term)]
        piv = g.pivot(index="target", columns="term", values="eta_sq").loc[["growth", "natural", "social"], terms]
        colors = {"C(region)": ps.SERIES[0], "C(period_label)": ps.SERIES[1], "C(size)": ps.SERIES[2],
                  "C(region):C(period_label)": ps.SERIES[6], "Residual": ps.GRID}
        left = np.zeros(len(piv))
        for term in terms:
            ax.barh(range(len(piv)), piv[term], left=left, color=colors[term], height=0.6,
                    edgecolor=ps.SURFACE, linewidth=2, label=nice[term])
            for i, v in enumerate(piv[term]):
                if v > 0.07:
                    ax.text(left[i] + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=8,
                            color=ps.INK if term == "Residual" else "#ffffff")
            left += piv[term].values
        ax.set_yticks(range(len(piv)), ["Total growth", "Natural", "Social"])
        ax.set_xlim(0, 1)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.grid(axis="y", visible=False)
        ax.set_title("Prefectures" if lv == "pref" else "Municipalities", fontsize=10)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8)
        ax.invert_yaxis()
    fig.suptitle("ANOVA: share of variation explained by region, period and size", x=0.01, ha="left",
                 fontweight="bold", fontsize=11)
    fig.tight_layout()
    ps.save(fig, "14_anova_variance_shares")

    # Tukey HSD: which regions differ in social change, municipalities 2015-2020.
    d = mu[mu.period == 2015]
    tk = pairwise_tukeyhsd(d.social, d.region)
    tkd = pd.DataFrame(tk.summary().data[1:], columns=tk.summary().data[0])
    tkd.to_csv(ROOT / "reports" / "tukey_region_social_2015.csv", index=False)
    means = d.groupby("region").social.agg(["mean", "median", "count"]).sort_values("mean")
    lines += ["### Tukey HSD: regions, municipal social change 2015–2020", "",
              "| Region | Mean | Median | n |", "|---|---|---|---|"]
    lines += [f"| {r} | {v['mean']:.2f} | {v['median']:.2f} | {int(v['count'])} |" for r, v in means.iterrows()]
    sig = tkd[tkd.reject == True]  # noqa: E712
    lines += ["", f"{len(sig)} of {len(tkd)} region pairs differ significantly (family-wise α = 0.05). "
              "Full table: `reports/tukey_region_social_2015.csv`.", ""]


def main() -> None:
    ps.apply()
    pref, muni = F.load_pref(), F.load_muni()
    pref = pref[pref.period >= 1985]  # income starts 1985
    lines = ["# Step 8a: explanatory models", "", "Generated by `python src/models.py`. "
             "Coefficients: effect of +1 standard deviation of a feature on the 5-year change, in percentage "
             "points, with standard errors clustered by area. ✱ = p < 0.05.", ""]
    coefs, plots_pref, plots_muni = [], [], []

    for t in F.TARGETS:
        feats = SEL["pref"][t]
        a, sa = fit(pref, t, feats, ["period"], "area_code", extra=["disaster_2011"])
        b, sb = fit(pref, t, feats, ["period", "pref"], "area_code", extra=["disaster_2011"])
        # Distance is measured at prefecture level, so prefecture fixed effects absorb it completely.
        mf = [f for f in SEL["muni"][t] if f != "log_dist_metro"]
        c, sc = fit(muni, t, mf, ["period", "pref"], "area_code")
        for tab, nm, s, lv in [(a, "A: period FE", sa, "pref"), (b, "B: period + prefecture FE", sb, "pref"),
                               (c, "period + prefecture FE", sc, "muni")]:
            tab["target"], tab["spec"], tab["level"] = t, nm, lv
            coefs.append(tab)
            lines += [f"## {'Prefectures' if lv == 'pref' else 'Municipalities'}: {t} change, {nm}", "",
                      f"n = {s['n']}, R² = {s['r2']:.2f}, within-R² (beyond fixed effects) = {s['within_r2']:.2f}", "",
                      "| Feature | Coef (pp per SD) | 95% CI | p |", "|---|---|---|---|"]
            for r in tab.sort_values("coef", key=abs, ascending=False).itertuples():
                lines.append(f"| {r.label} | {r.coef:+.2f}{' ✱' if r.p < 0.05 else ''} | "
                             f"[{r.lo:+.2f}, {r.hi:+.2f}] | {r.p:.3f} |")
            lines.append("")
        plots_pref += [("A: compare prefectures (period FE)", a), ("B: within prefecture (two-way FE)", b)]
        plots_muni += [("municipalities", c)]

    coef_plot(plots_pref, "What drives 5-year population change? Prefectures, 1985–2020", "12_coefficients_pref")
    coef_plot(plots_muni, "What drives 5-year population change? Municipalities, 1995–2020 "
                          "(within prefecture & period)", "13_coefficients_muni")
    pd.concat(coefs).to_csv(ROOT / "reports" / "coefficients.csv", index=False)
    anova(pref, muni, lines)
    (ROOT / "reports" / "models_explanatory.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
