# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

JAIST K417EJ course capstone: **factors of regional population decline in Japan**, using e-Stat data. Questions (from README): predict prefecture population 5–10 years ahead, find the factors contributing most (feature selection), link the onset of decline to historical events, and check whether the leading factors changed over time (~30, 20, 10 years ago vs. now).

## Repository layout

The whole project is **one notebook, `population_decline.ipynb`**, written to run in Google Colab. There are no scripts, build or tests.

- Run in Colab: the e-Stat key is a Colab secret `ESTAT_APP_ID`, read with `google.colab.userdata`. Never hard-code or commit the key (a local `.env` holds it and is git-ignored).
- Locally: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`; the first cell's `userdata` call only works in Colab.
- Sections: 1 data, 2 feature selection (+ 2b changing factors), 3 ANOVA, 4 prediction.

## Working style for this repo (important)

The user is learning and writes the notebook themselves, for readers who are not programmers.
- Keep code simple: short blocks, each starting with a one-line `#` comment; plain pandas/matplotlib/sklearn/statsmodels.
- Give small, explained pieces rather than generating large amounts of code; don't add new files or tooling unless asked.
- Prefer the methods taught in the course (regression, ANOVA). ANOVA follows the lecture's 7 steps: question → look at the data → checks (SD ratio < 2, Q-Q plot) → F test → η² → Tukey HSD → report; repeated measures for units measured several times.
- Test notebook changes by executing the notebook end to end before handing them over.

## Data conventions in the notebook

- Source: SSDS (statsCode `00200502`), prefecture tables `00000101xx` (raw counts) and `00000102xx` (rates). The `tables` dict maps short names to `table_id` + `item_code`.
- Download via the CSV endpoint `getSimpleStatsData` with `lang=E` and `sectionHeaderFlg=2`. Item codes starting with `#` must be URL-encoded (`quote()`), otherwise the request silently breaks.
- Area names are English with suffixes (`Akita-ken`, `Tokyo-to`, `Osaka-fu`, `Hokkaido`); `All Japan` is the national row. Keep `area_code` as a string (leading zeros).
- Survey-only statistics (housing in years ending 3/8, doctors every 2 years) are forward-filled for up to 4 years before building the 5-year table (`pref5`, census years 1975–2020).
- Fukushima after 2011 is flagged (`fukushima_after_2011`), not deleted: kept for charts over time, excluded from "why" analyses and models.
- Evaluation is always out-of-time: learn from earlier periods, test on later ones (feature selection: train 1985–2005, test 2010–2015 starts; forecasts: 2015→2020 for 5 years, 2010→2020 for 10 years).
- Vital Statistics (statsCode `00450011`) database tables by prefecture exist only in Japanese (`lang=J`); SSDS already contains births, deaths, fertility rate and marriages.

## Course materials

`Co-Creation AI` is a symlink to the course folder (lecture PDFs, project proposal, raw downloads). It is untracked; don't modify or commit anything through it.

## Note: the old full draft (reference only)

An earlier, much larger generated version (about 2,200 lines in `src/` scripts, municipal data for 1,741 towns, a births-vs-migration split, a birth-rate deep dive, a Shapley-R² factor analysis, and a written report with 24 figures) was **removed on 2026-11-23** in favour of this notebook. The user found it too complicated to learn from. It is recoverable from git history: the last commit that contains it is `d8d60c5` (`git show d8d60c5:reports/REPORT.md`, `git checkout d8d60c5 -- src`). Its published report page is still online at https://claude.ai/artifact/Y7UpUqDroR2EqgSa1WHhDi. Use it only as a reference for checking results or explaining a method; don't restore it into the repo unless asked.
