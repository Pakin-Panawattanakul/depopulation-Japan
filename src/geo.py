"""Static prefecture attributes: English name, region, capital coordinates, distances.

Coordinates are approximate (prefectural capital city halls, 2 decimals). They are used
only to compute distance to the big metropolitan cores.
"""

from __future__ import annotations

import math

import pandas as pd

# code: (english name, region, capital lat, capital lon)
PREFS = {
    "01": ("Hokkaido", "Hokkaido", 43.06, 141.35),
    "02": ("Aomori", "Tohoku", 40.82, 140.74),
    "03": ("Iwate", "Tohoku", 39.70, 141.15),
    "04": ("Miyagi", "Tohoku", 38.27, 140.87),
    "05": ("Akita", "Tohoku", 39.72, 140.10),
    "06": ("Yamagata", "Tohoku", 38.24, 140.36),
    "07": ("Fukushima", "Tohoku", 37.75, 140.47),
    "08": ("Ibaraki", "Kanto", 36.34, 140.45),
    "09": ("Tochigi", "Kanto", 36.57, 139.88),
    "10": ("Gunma", "Kanto", 36.39, 139.06),
    "11": ("Saitama", "Kanto", 35.86, 139.65),
    "12": ("Chiba", "Kanto", 35.61, 140.12),
    "13": ("Tokyo", "Kanto", 35.69, 139.69),
    "14": ("Kanagawa", "Kanto", 35.45, 139.64),
    "15": ("Niigata", "Chubu", 37.90, 139.02),
    "16": ("Toyama", "Chubu", 36.70, 137.21),
    "17": ("Ishikawa", "Chubu", 36.59, 136.63),
    "18": ("Fukui", "Chubu", 36.07, 136.22),
    "19": ("Yamanashi", "Chubu", 35.66, 138.57),
    "20": ("Nagano", "Chubu", 36.65, 138.18),
    "21": ("Gifu", "Chubu", 35.39, 136.72),
    "22": ("Shizuoka", "Chubu", 34.98, 138.38),
    "23": ("Aichi", "Chubu", 35.18, 136.91),
    "24": ("Mie", "Kinki", 34.73, 136.51),
    "25": ("Shiga", "Kinki", 35.00, 135.87),
    "26": ("Kyoto", "Kinki", 35.02, 135.76),
    "27": ("Osaka", "Kinki", 34.69, 135.52),
    "28": ("Hyogo", "Kinki", 34.69, 135.18),
    "29": ("Nara", "Kinki", 34.69, 135.83),
    "30": ("Wakayama", "Kinki", 34.23, 135.17),
    "31": ("Tottori", "Chugoku", 35.50, 134.24),
    "32": ("Shimane", "Chugoku", 35.47, 133.05),
    "33": ("Okayama", "Chugoku", 34.66, 133.93),
    "34": ("Hiroshima", "Chugoku", 34.40, 132.46),
    "35": ("Yamaguchi", "Chugoku", 34.19, 131.47),
    "36": ("Tokushima", "Shikoku", 34.07, 134.56),
    "37": ("Kagawa", "Shikoku", 34.34, 134.04),
    "38": ("Ehime", "Shikoku", 33.84, 132.77),
    "39": ("Kochi", "Shikoku", 33.56, 133.53),
    "40": ("Fukuoka", "Kyushu-Okinawa", 33.61, 130.42),
    "41": ("Saga", "Kyushu-Okinawa", 33.25, 130.30),
    "42": ("Nagasaki", "Kyushu-Okinawa", 32.74, 129.87),
    "43": ("Kumamoto", "Kyushu-Okinawa", 32.79, 130.74),
    "44": ("Oita", "Kyushu-Okinawa", 33.24, 131.61),
    "45": ("Miyazaki", "Kyushu-Okinawa", 31.91, 131.42),
    "46": ("Kagoshima", "Kyushu-Okinawa", 31.56, 130.56),
    "47": ("Okinawa", "Kyushu-Okinawa", 26.21, 127.68),
}
TOKYO_AREA = {"11", "12", "13", "14"}  # Saitama, Chiba, Tokyo, Kanagawa
METROS = {"Tokyo": (35.69, 139.69), "Osaka": (34.69, 135.52), "Nagoya": (35.18, 136.91)}


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def pref_table() -> pd.DataFrame:
    rows = []
    for code, (name, region, lat, lon) in PREFS.items():
        d = {m: haversine_km((lat, lon), xy) for m, xy in METROS.items()}
        rows.append({
            "pref": code, "pref_name": name, "region": region,
            "dist_tokyo_km": round(d["Tokyo"], 1),
            "dist_metro_km": round(min(d.values()), 1),  # nearest of Tokyo / Osaka / Nagoya
        })
    return pd.DataFrame(rows)
