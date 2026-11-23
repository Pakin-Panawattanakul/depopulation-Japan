"""Build a self-contained Google Colab notebook from the current pipeline code.

Usage:
    python src/make_colab_notebook.py     # -> notebooks/depopulation_japan_colab.ipynb

The notebook writes every src/*.py file and config/variables.csv into the Colab session with
%%writefile, asks for the e-Stat key, then runs steps 4-10 and shows the results inline.
Rerun this script after changing anything in src/ so the notebook stays in sync.
"""

from __future__ import annotations

import nbformat as nbf

from estat import ROOT

SRC_FILES = ["estat.py", "download.py", "geo.py", "build_panel.py", "plotstyle.py", "eda.py", "features.py",
             "select_features.py", "models.py", "forecast.py", "time_varying.py", "build_report.py",
             "report_template.html"]


def md(s: str):
    return nbf.v4.new_markdown_cell(s.strip())


def code(s: str):
    return nbf.v4.new_code_cell(s.strip())


def show_figs(*names: str) -> str:
    return ("from IPython.display import Image, display\n"
            f"for n in {list(names)!r}:\n"
            "    display(Image(f'reports/figures/{n}.png'))")


def show_md(path: str) -> str:
    return f"from IPython.display import Markdown, display\ndisplay(Markdown(open({path!r}).read()))"


def main() -> None:
    cells = [md("""
# Factors of regional population decline in Japan

JAIST K417EJ capstone. This notebook runs the whole analysis on Google Colab: it downloads data from the
e-Stat API (Social and Demographic Statistics System, SSDS), builds 5-year panels for 47 prefectures and
1,741 municipalities, and answers the four research questions:

1. When did regional decline start, and does it line up with historical events? (step 6)
2. Which factors contribute most? (steps 7–8)
3. Do the main factors change over time? (step 9)
4. How far will decline go by 2025 and 2030? (step 8b)

**Before you run:** add your e-Stat application ID as a Colab secret. Click the key icon in the left
sidebar, add a secret named `ESTAT_APP_ID`, and switch on *Notebook access*. If no secret is found, the
setup cell asks for the key instead.

Then use **Runtime → Run all**. The whole run takes about 10–15 minutes, most of it in the data download
(step 4) and the bootstrap feature selection (step 7).
"""),
             md("## Setup"),
             code("""
%pip install -q pyarrow python-dotenv statsmodels scikit-learn

import os, pathlib
ROOT = pathlib.Path(os.environ.get('PROJECT_DIR', '/content/depopulation-Japan'))
for d in ['src', 'config', 'data/raw/meta', 'data/processed', 'reports/figures']:
    (ROOT / d).mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)

key = os.environ.get('ESTAT_APP_ID')
if not key:
  try:
    from google.colab import userdata
    key = userdata.get('ESTAT_APP_ID')
  except Exception:
    pass
if not key:
    from getpass import getpass
    key = getpass('e-Stat application ID: ')
(ROOT / '.env').write_text(f'ESTAT_APP_ID={key.strip()}\\n')
os.environ['ESTAT_APP_ID'] = key.strip()
import subprocess, sys

def run(script, quiet=False):
    \"\"\"Run one pipeline step with this notebook's Python; stop with an error if it fails.\"\"\"
    r = subprocess.run([sys.executable, f'src/{script}'], capture_output=True, text=True)
    if not quiet or r.returncode:
        print(r.stdout[-6000:])
    if r.returncode:
        print(r.stderr[-6000:])
        raise RuntimeError(f'{script} failed (see the error above)')
    print(f'{script}: done')

print('Project folder:', ROOT)
"""),
             md("""
## Project code

The next cells write the pipeline's source files into the Colab session (`/content/depopulation-Japan/src`).
They're the same files as in the project repository. You don't need to read them to run the notebook.
""")]

    cfg = (ROOT / "config" / "variables.csv").read_text()
    cells.append(code(f"%%writefile config/variables.csv\n{cfg}"))
    for f in SRC_FILES:
        cells.append(code(f"%%writefile src/{f}\n" + (ROOT / "src" / f).read_text()))

    cells += [
        md("""
## Step 4: download data from e-Stat

Fetches every variable listed in `config/variables.csv`, at prefecture and municipal level. The municipal
data is the merger-adjusted series (current boundaries). Expect a few minutes.
"""),
        code("run('download.py')"),
        md("""
## Step 5: build the 5-year panels

Targets per period, as % of the starting population: total `growth`, `natural` change (births − deaths) and
`social` change (net migration, the residual). Features are measured at the start of each period.
Fukushima is dropped from 2010 (nuclear evacuation), and Miyake village for 1995–2005 (volcanic evacuation).
"""),
        code("run('build_panel.py')"),
        code("""
import pandas as pd
pref = pd.read_parquet('data/processed/pref_panel.parquet')
muni = pd.read_parquet('data/processed/muni_panel.parquet')
print(pref.shape, muni.shape)
pref.groupby('period_label')[['growth', 'natural', 'social']].mean().round(2)
"""),
        md("## Step 6: when did decline start? (exploratory analysis)"),
        code("run('eda.py', quiet=True)"),
        code(show_figs("01_national_population", "02_national_natural_change", "03_prefecture_peak_year",
                       "04_migration_blocs", "05_prefecture_growth_heatmap", "06_natural_vs_social",
                       "07_municipal_shrinking_share", "08_municipal_change_by_size", "09_feature_correlations")),
        md("""
## Step 7: feature selection

Within-period Lasso with bootstrap stability selection, random-forest permutation importance and VIF,
separately for natural and social change. This is the slowest step: about 5–10 minutes on Colab.
"""),
        code("run('select_features.py')"),
        code(show_figs("10_feature_stability_pref", "11_feature_stability_muni")),
        code(show_md("reports/feature_selection.md")),
        md("## Step 8a: what contributes most? (fixed-effects regressions and ANOVA)"),
        code("run('models.py', quiet=True)"),
        code(show_figs("12_coefficients_pref", "13_coefficients_muni", "14_anova_variance_shares")),
        code(show_md("reports/models_explanatory.md")),
        md("""
## Step 8b: forecasts to 2025 and 2030

Out-of-time backtests (each forecast uses only information available at its start year), compared with
naive persistence; then forecasts from 2020, checked against the official 2024 population estimates.
"""),
        code("run('forecast.py', quiet=True)"),
        code(show_figs("15_backtest_errors", "16_backtest_pref_2015", "17_forecast_pref")),
        code(show_md("reports/forecast.md")),
        md("## Step 9: do the main factors change over time?"),
        code("run('time_varying.py', quiet=True)"),
        code(show_figs("18_shapley_by_period_pref", "19_coef_paths_pref_social", "20_shapley_by_period_muni")),
        code(show_md("reports/time_varying.md")),
        md("""
## Step 10: report page and downloads

Builds the interactive report page (`reports/site/index.html`) and zips all results (figures, tables,
report, processed data) so you can download them or copy them to Google Drive.
"""),
        code("""
run('build_report.py')
!zip -qr results.zip reports data/processed config/selected_features.json
print('Wrote results.zip')
try:
    from google.colab import files
    files.download('results.zip')
except Exception:
    pass
"""),
        md("""
Optional: copy the results to Google Drive instead of downloading them.

```python
from google.colab import drive
drive.mount('/content/drive')
!cp -r reports /content/drive/MyDrive/depopulation-Japan-reports
```
"""),
    ]

    nb = nbf.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": [], "toc_visible": True},
    })
    out = ROOT / "notebooks" / "depopulation_japan_colab.ipynb"
    out.parent.mkdir(exist_ok=True)
    nbf.write(nb, out)
    print(f"wrote {out.relative_to(ROOT)} ({len(cells)} cells, {out.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
