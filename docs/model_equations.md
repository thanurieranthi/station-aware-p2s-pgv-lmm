# Model equations

All quantities are base-10 logarithms: PGV in cm/s (RotD50, horizontal), IV2 in cm²/s
(vertical-component P wave, 3-s window). Index j = record, s = station, c = NZS 1170.5 subsoil
class, e = earthquake event, y = calendar year. All models are fitted by maximum likelihood
(`lme4::lmer`, `REML = FALSE`, optimizer `bobyqa`).

| Model | Equation | R formula |
|---|---|---|
| OLS | log PGV = β0 + β1 log IV2 + ε | `log_PGV ~ log_IV2_3` |
| 1 (null) | log PGV = β0 + u0s + v0c + w0e + z0y + ε | `log_PGV ~ 1 + (1\|SiteClass) + (1\|StationName) + (1\|EarthquakeID) + (1\|Year_Index)` |
| 2 | + β1 log IV2 | `... + log_IV2_3` |
| 3 | + u1s log IV2 | `(1 + log_IV2_3 \| StationName)` |
| 4 | + w1e log IV2 | `(1 + log_IV2_3 \| EarthquakeID)` |
| 5 (operational) | log PGV = (β0 + u0s) + (β1 + u1s) log IV2 + ε | `log_PGV ~ 1 + log_IV2_3 + (1 + log_IV2_3 \| StationName)` |

Random effects are multivariate normal with zero mean; station intercept and slope are correlated.
For prediction, random effects of levels not seen in training (e.g. a new earthquake) are set to zero.

**ICC** (Suppl. Eq. S4): σ²_g / (σ²_g + σ²_residual), computed per grouping factor from the Model 1 variance components.
**Design effect** (Suppl. Eq. S5): 1 + (m̄ − 1)·ICC, m̄ = mean records per group.
