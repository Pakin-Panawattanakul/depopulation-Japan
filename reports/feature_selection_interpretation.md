# Step 7: interpretation of the feature-selection results

Written by hand after reviewing `reports/feature_selection.md` (which `src/select_features.py` regenerates).

**Prefectures, natural change** (CV R² 0.93): almost entirely explained by **age structure**.
- Aging rate (−) dominates the random-forest importance. Women 20–39 (+) is equally stable but was dropped because it correlates above 0.8 with aging rate; the two carry the same information.
- Total fertility rate (+) adds independent information (VIF 3).
- The remaining selected features (vacancy, high-school graduates leaving, income, job openings, unmarried rate, snow) have small coefficients. They're corrections, not drivers.

**Prefectures, social change** (CV R² 0.43; 0.60 for 2000+):
- Selected: **job-openings ratio (+), income (+), aging rate (−), unemployment (−), snow days (−)**. Migration follows jobs and income, and away from aging, snowy prefectures.
- ⚠ **Overlapping variables:** fiscal strength has the highest random-forest importance (0.27) but low Lasso stability (0.14). It overlaps with income and aging (VIF ≈ 15), and the Lasso keeps income in its place. Treat income as standing for an *economic-core* group (income, fiscal strength, land price, urban share, population size). Its individual members can't be told apart with 47 prefectures.
- Post-2000 (n = 186): the job-openings ratio stays on top. Vacancy, fiscal strength and university capacity enter. University outflow share is selected for natural change but not social change.

**Municipalities** (n ≈ 7,200): with this many observations nearly every feature passes the stability threshold, so rank by importance instead:
- **Natural change** (CV R² 0.87–0.89): aging rate, then distance to metro, then everything else.
- **Social change** (CV R² 0.20–0.34): **fiscal strength (+)** and **aging rate (−)** lead, then distance to metro, urban share, income.
- Social change is much noisier at municipal level: local events such as a factory, a university campus or a housing development aren't in the data.

**Overall:** natural change is predictable from today's age structure. Social change, the part policy can influence, is only partly explained, and mainly by local economic strength.
