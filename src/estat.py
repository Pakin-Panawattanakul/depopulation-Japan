"""Minimal e-Stat API v3 client with on-disk caching of metadata."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
META_DIR = ROOT / "data" / "raw" / "meta"
BASE = "https://api.e-stat.go.jp/rest/3.0/app/json"

load_dotenv(ROOT / ".env")


def _as_list(x) -> list:
    """e-Stat returns a dict instead of a one-element list; normalize."""
    if x is None:
        return []
    return [x] if isinstance(x, dict) else list(x)


def _get(endpoint: str, **params) -> dict:
    params["appId"] = os.environ["ESTAT_APP_ID"]
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=300)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt * 5)
    raise RuntimeError("unreachable")


def get_meta(stats_data_id: str, refresh: bool = False) -> dict:
    """Return METADATA_INF for a table, cached in data/raw/meta/."""
    META_DIR.mkdir(parents=True, exist_ok=True)
    path = META_DIR / f"{stats_data_id}.json"
    if refresh or not path.exists():
        path.write_text(json.dumps(_get("getMetaInfo", statsDataId=stats_data_id), ensure_ascii=False))
    j = json.loads(path.read_text())
    return j["GET_META_INFO"]["METADATA_INF"]


def classes(stats_data_id: str, class_id: str) -> pd.DataFrame:
    """One classification (e.g. 'cat01', 'area', 'time') as a DataFrame of its @-attributes."""
    for c in _as_list(get_meta(stats_data_id)["CLASS_INF"]["CLASS_OBJ"]):
        if c["@id"] == class_id:
            return pd.DataFrame(_as_list(c["CLASS"])).rename(columns=lambda s: s.lstrip("@"))
    raise KeyError(f"{class_id} not in {stats_data_id}")


def get_data(stats_data_id: str, cat01: list[str]) -> pd.DataFrame:
    """Download values for the given item codes, following pagination.

    Returns long format: code, area_code, time_code, value (float, NaN if not a number),
    raw (original string, keeps symbols like '***'), annotation.
    """
    rows: list[dict] = []
    start = 1
    while True:
        j = _get(
            "getStatsData",
            statsDataId=stats_data_id,
            cdCat01=",".join(cat01),
            startPosition=start,
            limit=100000,
            metaGetFlg="N",
        )["GET_STATS_DATA"]
        if j["RESULT"]["STATUS"] not in (0, 1):  # 1 = no data for this filter
            raise RuntimeError(f"{stats_data_id}: {j['RESULT']}")
        sd = j.get("STATISTICAL_DATA")
        if not sd or "DATA_INF" not in sd:
            break
        rows += _as_list(sd["DATA_INF"]["VALUE"])
        nxt = sd["RESULT_INF"].get("NEXT_KEY")
        if not nxt:
            break
        start = nxt
    if not rows:
        return pd.DataFrame(columns=["code", "area_code", "time_code", "value", "raw", "annotation"])
    df = pd.DataFrame(rows)
    out = pd.DataFrame(
        {
            "code": df["@cat01"],
            "area_code": df["@area"],
            "time_code": df["@time"],
            "raw": df["$"],
            "annotation": df.get("@anno"),
        }
    )
    out["value"] = pd.to_numeric(out["raw"].str.replace(",", ""), errors="coerce")
    return out
