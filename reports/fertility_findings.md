# Step 11: why are fewer babies born? Findings

Hand-written summary of `reports/fertility.md`, which `python src/fertility.py` regenerates. Prefecture level, census years 1985–2020. Figures 21–24.

## 1. The main reason is fewer marriages, not fewer children per couple

In Japan about 98% of births are to married parents.

| | 1980 | 2020 |
|---|---|---|
| Total fertility rate | 1.75 | 1.33 |
| Married share of women 25–39 | **84.5%** | **54.0%** |
| Births per 1,000 married women 20–44 | 92 | 101 (+9%) |

- **Married couples did not have fewer children.** Births per married woman went slightly *up*. The whole decline comes from fewer women being married (later marriage and no marriage).
- **The age-by-age check (1980→2005) agrees:**
  - fewer married women, by itself, would have cut the fertility rate by **0.80**;
  - more births per married woman added back **0.31**;
  - net change −0.48.
- **The same holds in 40 of 47 prefectures** (1985→2020).
- Caution: the women who still marry may be the ones who most want children, so "births per married woman" partly reflects who marries.

## 2. Why fewer marriages? Mainly jobs, income and housing

These are standardized effects, in percentage points of married share per 1 standard deviation. "Robust" means significant both between prefectures and within a prefecture over time.

| Factor | Between prefectures | Within a prefecture over time | Reading |
|---|---|---|---|
| Unemployment rate | **−0.89** | **−0.73** | robust: a weak job market means fewer marriages |
| Floor area of owned homes | **+1.19** | **+1.76** | robust: where homes are bigger, more people marry |
| Income per taxpayer | +0.48 (n.s.) | **+0.88** | when a prefecture's incomes rise, marriage rises |
| Men's wage | −0.41 (n.s.) | **+1.26** | the same for men's wages |
| Private rent | **−0.80** | −0.32 (n.s.) | expensive rent goes with fewer marriages |

By theme, **housing** explains the most variance between prefectures (37%), and **economy** the most within a prefecture over time (40%).

## 3. Why lower fertility in some places? Cities and the job market

- **Urban share** lowers fertility in both comparisons: −0.06 and −0.10 TFR per SD. It is also the strongest factor for births *per married woman* (−3.7 and −7.1 per 1,000). City couples have fewer children: high costs, small homes, long commutes.
- **Men's wage** points in opposite directions in the two comparisons:
  - richer prefectures such as Tokyo have *lower* fertility (−0.063);
  - when a prefecture's own wages rise, fertility goes *up* (+0.037).

  Level and change tell different stories: high-wage places are expensive cities, but improving pay helps.
- **The job market over time:** within a prefecture, higher unemployment lowers fertility (−0.034) and more job openings raise it (+0.015).
- **Childcare:** more nursery use goes with more births per married woman between prefectures (+3.0). Within a prefecture this is not significant.

## 4. What did *not* show a robust effect

- **Women working** (labor-force participation, dual-income couples, the women-to-men wage ratio): no consistent link with fertility or marriage. Every confidence interval includes zero in at least one comparison. In this data, women's employment is not what lowers birth rates.
- **Nuclear-family share:** the sign flips between the two comparisons, so it's not reliable.

## 5. Results that are probably reverse causation (don't read as causes)

- **Nurseries per 100k children** comes out negative. When the number of children falls, the same nurseries count as more per child, so low fertility *causes* the high ratio.
- **Nursery waiting list per 1,000 births** comes out positive, because more births create more demand for nursery places.

## 6. Answer in one paragraph

Japan has fewer babies mainly because **fewer young people marry**: the married share of women aged 25–39 fell from 85% to 54% between 1980 and 2020. Married couples still have about as many children as before. Marriage is lower where **jobs are insecure, incomes are low, and housing is small or expensive**, and it rises when a prefecture's job market and incomes improve. On top of that, **cities** have fewer children per couple. Women's employment shows no consistent negative effect.

## Limitations

- These are associations between prefecture averages (ecological data), measured in the same census year, so they don't prove causes.
- Wages are for all workers, not only young adults; the series by age stopped in 2008.
- There's no direct measure of non-regular (part-time or contract) employment, or of three-generation households.
- Individual-level reasons, such as values or the wish to marry, aren't in this data.
