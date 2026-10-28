# Station-aware P-to-S ground-motion estimation with linear mixed-effects models

Code, fitted models and derived data for:

> Eranthi, E. V. T., Lakraj, G. P., Ravishan, D., & Prasanna, R. — *A Mixed-Effects Modeling Approach for Station-Aware P-to-S Ground-Motion Estimation in Earthquake Early Warning*. Seismological Research Letters (in review).

The study predicts S-wave peak ground velocity (PGV, RotD50) from the first 3 s of the vertical P wave
(squared-velocity integral, IV2) using 40,797 GeoNet strong-motion records (10,079 earthquakes,
297 stations, New Zealand, 2013–2022). Linear mixed-effects models partition variability among
station, NZS 1170.5 subsoil class, earthquake event and calendar year; the operational on-site EEW model
keeps station-specific random intercepts and slopes:

$$\log_{10}\mathrm{PGV} = (\beta_0 + u_{0s}) + (\beta_1 + u_{1s})\,\log_{10}\mathrm{IV2}$$

with network-wide $\beta_0 = 0.9159$, $\beta_1 = 0.5272$ and per-station $u_{0s}, u_{1s}$ in
[`outputs/tables/station_coefficients_operational_model.csv`](outputs/tables/station_coefficients_operational_model.csv).

---

## Repository layout

```
.
├── run_all.R                     # reproduce the full statistical analysis
├── R/
│   ├── 00_config.R               # paths, seed, selection settings
│   ├── utils.R                   # tidy/export/metric helpers
│   ├── 01_load_and_filter.R      # record selection
│   ├── 02_split_train_test.R     # event-based 80:20 split
│   ├── 03_predictor_screening.R  # 18 candidate P-wave predictors (Table S1)
│   ├── 04_null_model_icc.R       # Model 1, ICC and design effect (Table 1)
│   ├── 05_mixed_models.R         # Models 2–4, likelihood-ratio tests (Table 2)
│   ├── 06_operational_model.R    # Model 5 + station coefficients (Table S5)
│   ├── 07_evaluate_test_set.R    # out-of-sample metrics (Table 3, Figs. 5–7)
│   └── 08_export_models.R        # .rds + CSV export of all models
├── python/processing/            # waveform download, QC and feature extraction
├── data/
│   ├── raw/metadata_log10_cm.csv # record-level feature table (input to R)
│   └── processed/                # train/test split written by the pipeline
├── outputs/
│   ├── models/                   # fitted model objects (.rds) + sessionInfo
│   └── tables/                   # machine-readable model coefficients and metrics
└── docs/
    ├── model_equations.md
    └── data_dictionary.md
```

## Fitted models

| File (`outputs/models/`) | Model | Paper |
|---|---|---|
| `model_ols.rds` | OLS, log PGV ~ log IV2 | Eq. 7 |
| `model_1_null.rds` | null model, random intercepts (station, subsoil, event, year) | Eq. 5, Table 1 |
| `model_2_random_intercepts.rds` | + log IV2 | Eq. 8 |
| `model_3_station_slope.rds` | + station random slope | Eq. 9, Table 4 |
| `model_4_station_event_slopes.rds` | + event random slope | Eq. 10 |
| `model_5_operational.rds` | station random intercept + slope only | Eq. 11, Table S5 |

Machine-readable tables (`outputs/tables/`):

| File | Content |
|---|---|
| `fixed_effects_all_models.csv` | fixed effects and standard errors, all models |
| `variance_components_all_models.csv` | variances, SDs, covariances/correlations, all mixed models |
| `station_coefficients_operational_model.csv` | per-station u0s, u1s (with conditional SDs), final intercept/slope, n training records, NZS 1170.5 class |
| `table_1_icc_design_effect.csv`, `table_2_model_comparison.csv`, `table_3_test_metrics.csv`, `table_S1_predictor_screening.csv` | tables of the paper |
| `operational_model_test_metrics.csv`, `station_test_metrics.csv` | test-set metrics for Model 5 and per station |

### Using a station's coefficients (no R needed)

```python
import pandas as pd, numpy as np
coef = pd.read_csv("outputs/tables/station_coefficients_operational_model.csv").set_index("station")
c = coef.loc["FJDS"]
log_iv2 = -4.0                                   # log10 IV2 (cm^2/s) from the first 3 s of P
log_pgv = c.final_intercept + c.final_slope * log_iv2   # log10 PGV (cm/s)
```

### Loading a fitted model in R

```r
library(lme4)
m5 <- readRDS("outputs/models/model_5_operational.rds")
predict(m5, newdata = data.frame(log_IV2_3 = -4, StationName = "FJDS"))
```

## Reproducing the analysis

Requirements: R ≥ 4.2 with `lme4`, `dplyr`, `performance` (see `outputs/models/sessionInfo.txt`).

```bash
Rscript run_all.R        # ~5 min; rewrites outputs/ and data/processed/
```

The waveform-processing scripts in `python/processing/` (ObsPy, h5py, SciPy, pandas) document how
`data/raw/metadata_log10_cm.csv` was produced from the GeoNet FDSN service; they require downloading
the raw waveforms and are not needed to reproduce the models. See `python/processing/README.md`.

## Data sources and licence

Waveforms and the earthquake catalogue are from GeoNet (GNS Science / Earth Sciences New Zealand):
waveform data https://doi.org/10.21420/G19Y-9D40, catalogue https://doi.org/10.21420/0S8P-TZ38,
used under CC BY 4.0. We acknowledge the New Zealand GeoNet programme and its sponsors NHC,
Earth Sciences NZ, LINZ, NEMA and MBIE.

- All contents — code (`R/`, `python/`, `run_all.R`), derived data (`data/`) and model outputs
  (`outputs/`) — are licensed under CC BY-NC 4.0 (Creative Commons Attribution-NonCommercial 4.0
  International) — see `LICENSE`. Use for research, teaching and other non-commercial purposes is
  permitted with attribution; commercial use is not. For commercial use, please contact the
  corresponding author.

## Citation

Please cite the article and this archive (see `CITATION.cff`; DOI: 10.5281/zenodo.23686243).
