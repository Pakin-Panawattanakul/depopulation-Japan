# Candidate datasets

Working list for plan steps 2–3. Edit freely.

- ✅ = checked against the e-Stat API on 2026-11-23 (table ID and real year coverage). ☐ = not checked yet.
- ★ = proposed core variable: one or two per theme, for the main model (target ~8–12 variables total, see [Modelling constraints](#modelling-constraints)).
- "5-yr" = available only in census or survey years (1975, 1980, … 2020).
- Metadata for every SSDS table is cached in `data/raw/meta/<statsDataId>.json` (git-ignored). It lists every item code and name.

## Backbone source: Social and Demographic Statistics System (SSDS, 社会・人口統計体系), confirmed

e-Stat statistics code `00200502`. Five series, each split into themed tables A–M (A population, B environment, C economy, D public finance, E education, F labour, G culture, H housing, I health, J welfare, K safety, L household economy, M time use):

| Series | statsDataId | Areas | Years | Items |
|---|---|---|---|---|
| Prefecture: raw values (基礎データ) | `00000101xx` (A=01 … M=13) | 47 + national | 1975–2025 | ~4,800 |
| Prefecture: indicators, i.e. rates and ratios (社会生活統計指標) | `00000102xx` | 47 + national | 1975–2024 | ~600 |
| Municipality: raw values, original boundaries | `00000201xx` (A–K) | 3,818 | 1980–2024 | |
| **Municipality: raw values, merger-adjusted (廃置分合処理済)** | `00000202xx` | **1,913** | 1980–2024 | ~800 |
| **Municipality: indicators, merger-adjusted** | `00000203xx` | 1,913 | 5-yr, 1980–2023 | ~100 |

**Key finding:** e-Stat has already redrawn municipal data onto **current boundaries**, so the Heisei-merger problem is solved for us. The 1,913 areas include the wards of designated cities (e.g. 札幌市 中央区) alongside the cities themselves, so we must drop one or the other to avoid double counting.

## Main constraint the data imposes: the census rhythm

Many variables (age structure, unemployment, densely inhabited districts, vacancy, and all municipal population) exist **only every 5 years**. So:
- **Main time unit = 5-year periods** (1975→80, …, 2015→20). That gives 47 × 9 = **423 prefecture observations**, or about 1,700 × 5 = **~8,500 municipal observations** (1995–2020).
- Yearly variables are averaged or sampled within each 5-year period.

---

## 0. Target variable: what we predict and explain

Split population change into its two parts, because they have different causes:

```
Δ population = natural change (births − deaths) + social change (moves in − moves out)
```

| Variable | Code / table | Pref | Muni | ✓ |
|---|---|---|---|---|
| Total population | `A1101` | yearly 1975–2024 | 5-yr 1980–2020 | ✅ |
| Births | `A4101` | yearly 1980–2023 | yearly 1995–2023 | ✅ |
| Deaths | `A4200` | yearly 1975–2023 | yearly 1980–2023 | ✅ |
| Moves in / out (Japanese nationals) | `A5101` / `A5102` (muni: `A5103` / `A5104`) | yearly 1975–2025 | **only 2018–2024** | ✅ |
| Natural change rate (ready-made) | `#A05201`, table `0000010201` | yearly 1980–2022 | – | ✅ |
| Social change rate (ready-made) | `#A05306` | only 2018–19, so compute it ourselves | – | ✅ |
| Official projections (baseline to beat) | IPSS regional projections (地域別将来推計人口), not on e-Stat | ✓ | ✓ | ☐ |

**Municipal migration workaround:** moves in and out exist only from 2018, but the residual works instead: *net migration = Δ population − (births − deaths)* over each 5-year census interval. Births start in 1995, so this covers 1995–2020.

## 1. Demographic structure

| Variable | Why it might matter | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| ★ Aging rate (65+ share) | More elderly → more deaths, fewer births | `A1303` / `A1101` (ready-made `A1306` only from 2005) | yearly 1975+ | 5-yr 1980–2020 | ✅ |
| ★ Women aged 20–39 | Mothers of the next generation; basis of the 2014 "Masuda report" list of municipalities at risk of disappearing (消滅可能性都市) | `A120502`–`A120802` (4 age bands) | yearly 1975–2024 | ✗ no 20–39 band; only women 15–64 (`A130202`, 5-yr 2000–2020) | ✅ |
| Total fertility rate (TFR) | Direct driver of births | `#A05203` | yearly 1980–2023 | ✗ | ✅ |
| Unmarried rate, women 30–34 | Very few births outside marriage in Japan | `A1601042` / `#A0410502` | 5-yr 1980–2020 | overall rate only (`A161001`) | ✅ |

⚠ **Reverse causality:** aging is partly a *result* of young people leaving. Use values from the *start* of each period (e.g. 2010 values → 2010–2015 change).

## 2. Economy and employment

| Variable | Why | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| ★ Taxable income per taxpayer | People move toward higher income | `C120110` / `C120120` | yearly 1985–2024 | yearly 1985–2024 (1,742 areas) | ✅ |
| Prefectural income per person (県民所得) | | `C120101` (2005 base, 2001–2014 only; other base years exist, so the series must be chained) | partial | ✗ | ✅ |
| ★ Job-openings ratio (有効求人倍率) | Availability of jobs | `F310301`: **only 2015–2024 in SSDS** → need the long MHLW series from outside e-Stat | short | ✗ | ✅ |
| Unemployment rate | | `#F01301` | 5-yr 1975–2020 | 5-yr 1980–2020 | ✅ |
| Industry mix (primary / tertiary share) | Farming regions decline | `C2105`/`C2110`…; definitions change in 2009 (old business survey → Economic Census) | ✓ | ✓ | ✅ exists |
| Average wage | | `F620…` (所定内給与額) | ✓ | ✗ | ☐ coverage |
| Minimum wage | Large prefecture gaps | MHLW, not SSDS | ✓ | – | ☐ |

## 3. Urbanization and geography

| Variable | Why | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| ★ Share living in densely inhabited districts (DID) | Urban vs. rural | `A1801` / `A1101` | 5-yr 1975–2020 | 5-yr; only 670 municipalities have a DID, so treat the rest as 0 | ✅ |
| ★ Distance to Tokyo / nearest major city | Peripheral regions lose people | build ourselves | ✓ | ✓ | – |
| Population density on habitable land | | `#A01202` | ✓ | ✓ | ✅ exists |
| Shinkansen / airport opening year | Natural experiment (does a new line drain people to the big city, the "straw effect"?) | build ourselves | ✓ | ✓ | – |

## 4. Housing and land

| Variable | Why | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| ★ Vacancy rate | Symptom and accelerator of decline | `#H01405` | 5-yr 1978–2023 | 5-yr 2003–2023, ~1,256 areas (small villages missing) | ✅ |
| Residential land price | Weak demand; or pushes people out of big cities | `C5401` | yearly 1976–2024 | only 1993–2009 | ✅ |

## 5. Education

| Variable | Why | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| ★ Share of high-school graduates entering university in *another* prefecture | Probably the biggest moment young people leave | `E470202` / `E470205` | yearly **2000–2024** | ✗ | ✅ |
| Same idea, ready-made: share entering a local university | | `#E0940302` | ☐ coverage | ✗ | ✅ exists |
| University capacity index (大学収容力指数) | Local options to stay | `#E0610202` | yearly 1976–2024 | ✗ | ✅ |

## 6. Health, welfare and childcare

| Variable | Why | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| ★ Doctors per 100k | Quality of life; elderly care | `I6100` / population | 28 yrs, 1975–2022 (every 2 yrs) | 25 yrs, 1984–2022 | ✅ |
| Childcare places per child | Whether families can raise kids there | `#E0110105` | ☐ coverage | partial | ✅ exists |

## 7. Public finance and policy

| Variable | Why | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| ★ Fiscal strength index (財政力指数) | Dependence on central-government transfers | `D2101` (pref) / `D2201` (muni) | yearly 1975–2022 | yearly 1980–2022, but only ~1,132 areas, so check what's missing | ✅ |
| Hometown-tax donations received (ふるさと納税) | Recent extra local revenue | MIC, not SSDS | ✓ | ✓ | ☐ |

## 8. Environment and disasters

| Variable | Why | Code | Pref | Muni | ✓ |
|---|---|---|---|---|---|
| Days of snowfall | Harsh winters (Tohoku, Hokuriku, Hokkaido) | `B4107` | yearly 1975–2020 | ✗ | ✅ |
| Major-disaster indicator | 2011 Tohoku, 1995 Kobe | build ourselves | ✓ | ✓ | – |

---

## Historical events (for interpretation, step 6, mostly not model inputs)

| Year | Event | Expected effect |
|---|---|---|
| 1973 | Oil shock; end of rapid growth | Migration to the big cities slows |
| 1986–91 | Bubble economy | Strong flow into Tokyo |
| 1991– | Bubble bursts; "lost decades" | Regional economies weaken |
| 1995 | Kobe earthquake | Local shock in Hyogo |
| 1999–2010 | Great Heisei Mergers | (Already handled by SSDS merger-adjusted data) |
| 2005 | Japan's total population first falls | |
| 2008 | Global financial crisis (Lehman shock) | Manufacturing regions hit |
| 2011 | Tohoku earthquake, tsunami, Fukushima | Large outflow from Fukushima, Miyagi, Iwate |
| 2014 | Masuda report; regional revitalization policy (地方創生) | Did anything change after it? |
| 2020– | COVID-19, remote work | First net outflow from Tokyo's 23 wards, ~2021 |

---

## Modelling constraints

- **Panel data with 5-year periods**: 423 prefecture observations (1975–2020), ~8,500 municipal (1995–2020). Fixed-effects models.
- **Core model ~8–12 variables** (the ★ items). Use the rest for robustness checks or within-theme summary scores (PCA).
- **Inputs from the start of the period** only, for forecasting and to limit reverse causality.
- **Time span is now set by the data**: prefectures 1975–2020 (Okinawa included; SSDS covers it from 1975), municipalities 1995–2020.

## Decisions

Agreed 2026-11-23. Revisit any of them if results suggest it.

### D1. Fukushima after 2011: drop
**Decision:** exclude Fukushima prefecture from every 5-year period from **2010→2015 onward**, at both prefecture and municipal level. Keep all periods up to 2005→2010.

**Why:** after the nuclear accident, population change there was driven by evacuation orders, not by the economic and social factors we study. In SSDS data, Fukushima's net migration jumped from about −8k/yr (2006–10) to −31k in 2011, and towns such as Futaba, Okuma, Namie and Tomioka were recorded at 0 people in the 2015 census. Left in, these would dominate the regression.

**Notes:**
- Miyagi and Iwate stay in. Their 2011 shock is mainly tsunami deaths plus a reconstruction-worker inflow (Miyagi net migration +6k in 2012). Proposed: add a disaster indicator for the 2010→2015 period for both prefectures.
- Consequence: the models say nothing about Fukushima after 2010, and we make no forecast for it. State this in the report.
- If we later want to keep the rest of Fukushima, the evacuation-order municipalities to drop would be the standard 12 (避難指示等対象12市町村): Tamura, Minamisoma, Kawamata, Hirono, Naraha, Tomioka, Kawauchi, Okuma, Futaba, Namie, Katsurao, Iitate.

### D2. Tokyo area: no separate model (for now)
**Decision:** one model, including Tokyo, Kanagawa, Saitama and Chiba.

**Note:** Tokyo is the main destination of migration and an extreme value on many variables, so check whether it has outsized influence (e.g. Cook's distance, residual plots) in step 8. If it does, reopen this decision.

### D3. Job-openings ratio: fetch the long series from outside e-Stat
**Decision:** SSDS only has `F310301` from 2015, so fetch the full yearly series by prefecture from MHLW's job placement statistics (一般職業紹介状況). It goes back several decades.

**To do:** find the download source and its format; check that its definition matches the SSDS values for 2015–2024 where they overlap.

### D4. Out-of-prefecture university entry: post-2000 models only
**Decision:** use `E470202` / `E470205` in the models that cover 2000 onward. Leave it out of the full 1975–2020 model.

**Why not fill earlier years with 0:** a 0 would mean "no student left the prefecture", which is false, and the model would treat pre-2000 prefectures as if nobody left for university. If one model must cover all years, use the standard *missing-indicator* approach instead: fill earlier years with a constant and add a flag `univ_data_available` (0 before 2000, 1 after), so the model can separate "no data" from "low value".

**Possible later improvement:** older School Basic Survey (学校基本調査) tables may have the same figure before 2000. Worth a search if this variable turns out to matter.

### D5. Designated cities: analyse whole cities, not wards
**Decision:** use the 20 designated cities (政令指定都市, e.g. Sapporo, Sendai, Yokohama, Osaka) as single units, and drop their wards (行政区) from the municipal data.

**Why:** wards are administrative divisions, not independent municipalities, and much municipal data (fiscal strength, for example) exists only for the whole city. Including both cities and their wards would double-count people.

**Note:** Tokyo's 23 special wards (特別区) **are** separate municipalities, so keep them as individual units.

### D6. Other evacuated areas: Miyake village 1995–2005 (added in step 5)
**Decision:** drop Miyake village (三宅村, Tokyo, `13381`) for the periods starting 1995 and 2000. After the 2000 Miyakejima eruption the whole island was evacuated, so the 2000 census counted 0 people. That's the same reason as D1: the change was caused by an evacuation order, not by the factors we study.

### D7. Job-openings ratio: found in SSDS (updates D3)
`#F03103` (table `0000010206`) is the long series, 1975–2022, so no outside MHLW download is needed. Also added: `#F03302`, the share of high-school graduates taking a job in another prefecture (1975–2023). It measures young people leaving before 2000, when the university-outflow variable (D4) doesn't exist yet.
