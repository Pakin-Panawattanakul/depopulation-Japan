# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

JAIST K417EJ course capstone: **factors of regional population decline in Japan**, using data from e-Stat (e-stat.go.jp). Planned work (from README):
- Predict regional population 5 or 10 years ahead
- Identify the factors contributing most to depopulation (attribute/feature selection)
- Interpretation: link the onset of decline to historical events; check whether the dominant factors shift over time (e.g. 30, 20, 10 years ago vs. now)

Implementation language is **Python**. The user has an e-Stat API key — read it from an environment variable or an untracked file, never hard-code or commit it.

## Environment

Plain `venv` + `requirements.txt` (system Python 3.14; no uv/conda installed).

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # setup
source .venv/bin/activate                                           # activate
jupyter lab                                                         # notebooks; kernel "Python (depopulation-Japan)"
cp .env.example .env                                                # then set ESTAT_APP_ID
```

No lint or test setup exists yet.

## Pipeline

```sh
python src/download.py                 # step 4: fetch SSDS variables -> data/raw/ssds_{pref,muni}.parquet
python src/download.py --level pref --refresh
python src/build_panel.py              # step 5: -> data/processed/{pref_yearly,pref_panel,muni_panel,*_start_2020}.parquet
python src/eda.py                      # step 6: figures 01-09, reports/eda_summary.json
python src/select_features.py          # step 7: -> config/selected_features.json (~2 min: bootstrap + RF)
python src/models.py                   # step 8a: FE regressions + ANOVA, reads selected_features.json
python src/forecast.py                 # step 8b: backtests + 2025/2030 forecasts
python src/time_varying.py             # step 9: per-period Shapley R2, interaction F-tests
python src/build_report.py             # step 10: reports/site/index.html from src/report_template.html
```

Steps depend on earlier outputs in this order. `reports/REPORT.md` is the written summary; the numbers quoted in it and in `src/report_template.html` were copied from the generated `reports/*.md`, so update both texts if a rerun changes results. Shared feature lists and transforms live in `src/features.py`; chart styling (colour-blind-checked palette) in `src/plotstyle.py`. Published report page: https://claude.ai/artifact/Y7UpUqDroR2EqgSa1WHhDi (republish `reports/site/index.html` to update it).

Scripts in `src/` import each other as plain modules (`import estat`), so run them as `python src/<script>.py` from the repo root.

### Panel conventions (step 5, `src/build_panel.py`)
- **Unit = 5-year period** starting at a census year t. Prefecture periods start 1980–2015 (births start in 1980); municipal periods start 1995–2015 (municipal births start in 1995).
- **Targets**, in % of the population at t: `growth`, `natural` (births − deaths, summed over years t+1..t+5, the window that best matched population change), and `social` = growth − natural. This residual correlates 0.97 with recorded moves in and out.
- **Features are measured at year t.** Survey-year variables carry the latest value forward for up to 5 years. Money values are expressed relative to the national level (`*_rel`, national = 100), which removes inflation.
- **Exclusions:** Fukushima from 2010 (D1); Miyake village (13381) for 1995 and 2000 (fully evacuated after the 2000 eruption).

- `config/variables.csv` decides what gets downloaded (one row per variable × level). Add a variable by adding a row with its SSDS item code. `download.py` finds the right table by searching the cached metadata.
- `src/estat.py` is the API client. `data/raw/ssds_manifest.json` records the source table and actual year coverage for each variable.
- Raw output is long format: `variable, area_code, area_name, area_level, year, value, raw, annotation, source_table`. `raw` keeps the original string; `-` means no value.

### Municipal area codes (needed for step 5)
- `area_level` 2 = city, town or village, plus `13100` (an aggregate of all Tokyo wards, 東京都 特別区部). `area_level` 3 = wards: the 194 wards of designated cities and Tokyo's 23 special wards (`13101`–`13123`).
- Decision D5 (whole cities) → keep level 2 except `13100`, and add the 23 Tokyo wards from level 3. That gives 1,741 units.
- Ratio variables such as `fiscal_strength` exist only for about 1,124 areas before 2005: merged municipalities have no pre-merger values, because ratios can't be added together the way counts can. Count variables are fully merger-adjusted.

## Research design

`docs/datasets.md` is the working list of candidate variables, grouped by theme. It also records the agreed design choices: modelling population change as natural change plus migration, prefecture × year panel data with ~8–12 core variables, inputs taken only from before the outcome period, and the open decisions. Keep it updated as datasets are checked and decisions are made.

## Data and course materials

`Co-Creation AI` is a **symlink** to `/home/pakin/JAIST/Co-Creation AI` (outside the repo, untracked). It holds:
- Course lecture PDFs (Python, Regression, ANOVA, Text Mining). These show which analysis methods the course expects, so prefer them over more exotic techniques.
- `CapstoneProjectProposal.doc`: the project proposal
- Raw data downloads: `ct2025.xlsx`, `staj2022.xlsx`, and e-Stat CSV exports `FEH_00200522_*.csv` (2023 Housing and Land Survey, dwellings by occupancy status, by prefecture and 21 major cities)

Don't modify or commit files through the symlink. Copy data into the repo, or reference it by path.

### e-Stat API

- REST v3 JSON: `https://api.e-stat.go.jp/rest/3.0/app/json/{getStatsList|getMetaInfo|getStatsData}`, with `appId` from `ESTAT_APP_ID` in `.env`.
- `getStatsData` returns at most 100,000 values per call. Follow `RESULT_INF.NEXT_KEY` by passing it as `startPosition`. Filter items with `cdCat01=<code>,<code>`.
- A single-element result comes back as a dict instead of a list, so normalize `VALUE`/`CLASS`/`TABLE_INF` before use.
- `load_dotenv()` with no path fails for scripts piped via stdin. Pass `load_dotenv(".env")`.
- Main source: SSDS (statsCode `00200502`). The table IDs and the variables checked so far are listed in `docs/datasets.md`. Use the **merger-adjusted** municipal series (`00000202xx`, `00000203xx`), not the original-boundary one (`00000201xx`).
- Raw downloads and metadata go in `data/raw/` (git-ignored).

### e-Stat CSV export format

The `FEH_*.csv` downloads aren't plain tables. Parsing needs to handle:
- About 10 metadata rows at the top (statistics name, table number, title, date, legend for special symbols), then two code-header rows (`/... Code`, `/... Auxiliary Code`), then the real column header row
- Each dimension comes as `Code` / `Auxiliary Code` / label column triples (e.g. area code `00000` = Japan, prefecture codes)
- Numbers use comma thousands separators (`"65,046,700"`)
- Missing or suppressed values are marked `***`, `-`, `...`, `X` and must become NaN
- Area codes have leading zeros (`01000`), so read code columns as `str`

Working starting point for these files (header is on line 14):
```python
pd.read_csv(path, skiprows=13, thousands=",", na_values=["***", "-", "...", "X"],
            dtype={"Japan, Prefectures, 21 Major Cities Code": str})
```
