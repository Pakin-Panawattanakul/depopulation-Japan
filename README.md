# JAIST K417EJ Course capstone project : Factors of regional population decline in Japan

Dataset from e-stat.go.jp: Social and Demographic Statistics System (SSDS), Statistics Bureau of Japan.
47 prefectures, 1975–2024.

## What we planned to do
- Predict population in 5 or 10 years
- Find what contributes the most to depopulation
- Attribute (feature) selection

## Interpretation
- Can we associate historical events with when population started to decline?
- Changing of the most contributing factors: 30, 20, 10 years ago and now

## The notebook: `population_decline.ipynb`
1. **Get and prepare the data**: download from the e-Stat API, combine, calculate rates, regions, 5-year table
2. **Feature selection**: correlation, random forest and Lasso, compared on a 2010–2020 test
   - **2b. Changing factors**: correlation per period (~30, 20, 10 years ago and now)
3. **ANOVA**: one-way by region (7 steps from class) and repeated measures over periods
4. **Prediction**: naive, linear regression and random forest, 5 and 10 years ahead; forecast to 2025 and 2030

## How to run
1. Open `population_decline.ipynb` in Google Colab (File → Upload notebook)
2. Add your e-Stat key as a Colab secret: key icon on the left → name `ESTAT_APP_ID` → turn on *Notebook access*
3. Runtime → Run all (under a minute)

To run on your own computer instead: `pip install -r requirements.txt`, and in the first code cell
replace `userdata.get("ESTAT_APP_ID")` with your key (don't commit it).
