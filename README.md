# Factors of regional population decline in Japan

JAIST K417EJ course capstone project.

Japan's population peaked in 2008, and most of its 47 prefectures are now shrinking. This project uses
official statistics to ask:

1. **Which factors are linked to population decline?** (feature selection)
2. **Have the leading factors changed?** About 30, 20 and 10 years ago vs. now
3. **Do regions and periods differ?** (ANOVA)
4. **How will each prefecture's population change** over the next 5 and 10 years?

## Data

**Social and Demographic Statistics System (SSDS, 社会・人口統計体系)**, Statistics Bureau of Japan, downloaded
through the [e-Stat API](https://www.e-stat.go.jp/api/).
- 47 prefectures, 1975–2024
- 31 statistics, one or two per topic: population, family, land and weather, income, jobs, public finance,
  education, culture, housing, health, welfare, safety
- Tables used: `0000010101`–`0000010212` ([list of SSDS tables](https://www.e-stat.go.jp/stat-search/database?toukei=00200502))

## The notebook: `population_decline.ipynb`

Everything is in one notebook, written in short blocks, each starting with a comment.

| Section | What it does |
|---|---|
| 1. Get and prepare the data | download from e-Stat, combine into one table, turn counts into rates, add regions, build a 5-year table |
| 2. Feature selection | correlation, random forest and Lasso each pick their top 5; the best method is chosen by test error on 2010–2020 |
| 2b. Changing factors | the same correlation, separately for ~30, 20 and 10 years ago and now, with a heatmap |
| 2c. Is the link real? | regression with other factors held fixed, and within each prefecture over time |
| 3. ANOVA | one-way ANOVA by region (the 7 steps from class) and repeated-measures ANOVA over periods |
| 4. Prediction | naive, linear regression and random forest, 5 and 10 years ahead; forecasts to 2025 and 2030 |

## Main results (run of November 2026)

- **Feature selection:** random forest's top 5 predicted best: aging rate, fiscal strength, marriage rate,
  doctors, hospitals. All three methods agree on aging rate and marriage rate. Using all 18 statistics predicted
  worse than any top 5.
- **Changing factors:** aging is the strongest factor in every period and keeps getting stronger
  (correlation −0.72 → −0.92). Income mattered most ~30 years ago; marriage rate and the local tax base
  (fiscal strength) matter most now. City density became more important (+0.24 → +0.69).
- **Is the link real?**
  - Traffic accidents show no link.
  - Income goes with lower fertility only between places (cities vs. countryside).
  - When a prefecture's own unemployment rises, its fertility falls.
- **ANOVA:**
  - Population change 2015–2020 differs by region: F(6, 39) = 4.47, p = 0.002, η² = 0.41.
  - Tukey: Kanto differs from Hokkaido-Tohoku and from Shikoku.
  - Repeated measures: the change differs strongly between periods (F = 165).
- **Prediction:**
  - 5 years: simply repeating the recent trend was best (error 0.55 percentage points).
  - 10 years: linear regression was best (0.79 vs. 1.93 for the trend).
  - Forecast for the 46 prefectures: 124.3 million (2020) → 120.4 million (2030).
  - Check against the real 2024 population: correlation 0.97, but actual decline is faster than forecast.

**Notes:**
- Fukushima after 2011 is left out of the "why" analyses and the models, because its decline was caused by the
  nuclear evacuation.
- All results are associations from prefecture averages, not proof of cause.

## How to run

**Google Colab**
1. File → Upload notebook → `population_decline.ipynb`
2. Add your e-Stat key as a secret: key icon on the left → name `ESTAT_APP_ID` → turn on *Notebook access*
3. Runtime → Run all (about a minute)

**Your own computer (Jupyter)**
1. Put your key in a file named `.env` in this folder: `ESTAT_APP_ID=your_key` (it is git-ignored)
2. First time only: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. `source .venv/bin/activate`, then `jupyter lab`
4. Open `population_decline.ipynb` → Run → Run All Cells

Get a free e-Stat key at https://www.e-stat.go.jp/api/. Never put the key in the notebook itself.

## Files

| File | |
|---|---|
| `population_decline.ipynb` | the whole analysis |
| `requirements.txt` | Python libraries (Colab already has them) |
| `.gitignore` | keeps your key (`.env`), the virtual environment and the CSV files out of git |
