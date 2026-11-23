"""Step 4: download SSDS variables listed in config/variables.csv.

Usage:
    python src/download.py              # all levels
    python src/download.py --level pref
    python src/download.py --refresh    # re-download even if output exists

Output (long format, one row per variable x area x year):
    data/raw/ssds_pref.parquet, data/raw/ssds_muni.parquet
    data/raw/ssds_manifest.json  (source table per variable, download date, coverage)
"""

from __future__ import annotations

import argparse
import json
from datetime import date

import pandas as pd

import estat

# SSDS table series searched for each level (table suffixes 01..13 = themes A..M).
# Municipal series are the merger-adjusted ones (廃置分合処理済), see docs/datasets.md.
SERIES = {
    "pref": [f"00000101{i:02d}" for i in range(1, 14)] + [f"00000102{i:02d}" for i in range(1, 14)],
    "muni": [f"00000202{i:02d}" for i in range(1, 12)] + [f"00000203{i:02d}" for i in range(1, 12)],
}
RAW = estat.ROOT / "data" / "raw"


def item_index(level: str) -> dict[str, tuple[str, str, str]]:
    """Map item code (name prefix, e.g. 'A1101', '#A05203') -> (statsDataId, cat01 code, Japanese name)."""
    idx: dict[str, tuple[str, str, str]] = {}
    for sid in SERIES[level]:
        for _, row in estat.classes(sid, "cat01").iterrows():
            code = row["name"].split("_", 1)[0]
            idx.setdefault(code, (sid, row["code"], row["name"]))
    return idx


def area_table(sid: str) -> pd.DataFrame:
    a = estat.classes(sid, "area")
    cols = {"code": "area_code", "name": "area_name"}
    if "level" in a:
        cols["level"] = "area_level"
    return a[list(cols)].rename(columns=cols)


def download_level(level: str) -> tuple[pd.DataFrame, list[dict]]:
    spec = pd.read_csv(estat.ROOT / "config" / "variables.csv")
    spec = spec[spec["level"] == level]
    idx = item_index(level)

    missing = [c for c in spec["code"] if c not in idx]
    if missing:
        print(f"[{level}] WARNING: codes not found in SSDS, skipped: {missing}")
    spec = spec[spec["code"].isin(idx)].copy()
    spec["sid"] = spec["code"].map(lambda c: idx[c][0])
    spec["cat01"] = spec["code"].map(lambda c: idx[c][1])
    spec["name_ja"] = spec["code"].map(lambda c: idx[c][2])

    frames = []
    for sid, g in spec.groupby("sid"):
        print(f"[{level}] {sid}: {', '.join(g['name'])}")
        df = estat.get_data(sid, list(g["cat01"]))
        df = df.merge(g[["cat01", "name"]], left_on="code", right_on="cat01").drop(columns=["cat01", "code"])
        df = df.merge(area_table(sid), on="area_code", how="left")
        df["source_table"] = sid
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    out["year"] = out["time_code"].str[:4].astype(int)
    out = out.rename(columns={"name": "variable"})
    out = out[["variable", "area_code", "area_name", *(["area_level"] if "area_level" in out else []),
               "year", "value", "raw", "annotation", "source_table"]]
    out = out.sort_values(["variable", "area_code", "year"]).reset_index(drop=True)

    manifest = []
    for _, s in spec.iterrows():
        v = out[(out["variable"] == s["name"]) & out["value"].notna()]
        years = sorted(v["year"].unique().tolist())
        manifest.append({
            "variable": s["name"], "code": s["code"], "name_ja": s["name_ja"], "source_table": s["sid"],
            "n_years": len(years), "first_year": years[0] if years else None,
            "last_year": years[-1] if years else None, "years": years,
            "areas_per_year_median": int(v.groupby("year")["area_code"].nunique().median()) if years else 0,
        })
    return out, manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=["pref", "muni"], action="append")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    levels = args.level or ["pref", "muni"]

    RAW.mkdir(parents=True, exist_ok=True)
    mpath = RAW / "ssds_manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}

    for level in levels:
        path = RAW / f"ssds_{level}.parquet"
        if path.exists() and not args.refresh:
            print(f"[{level}] {path.name} exists, skipping (use --refresh)")
            continue
        df, man = download_level(level)
        df.to_parquet(path, index=False)
        manifest[level] = {"downloaded": date.today().isoformat(), "rows": len(df), "variables": man}
        print(f"[{level}] saved {len(df):,} rows -> {path.relative_to(estat.ROOT)}")
        for m in man:
            span = f"{m['first_year']}-{m['last_year']}" if m["n_years"] else "NO DATA"
            print(f"    {m['variable']:<26} {span:<10} {m['n_years']:>3} yrs  {m['areas_per_year_median']:>5} areas")

    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
