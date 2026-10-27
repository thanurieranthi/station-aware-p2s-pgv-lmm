#!/usr/bin/env Rscript
# =============================================================================
# run_all.R — reproduce the statistical analysis end to end
#   Usage (from the repository root):  Rscript run_all.R
# =============================================================================

suppressPackageStartupMessages({
  library(lme4)
  library(dplyr)
  library(performance)
})

steps <- c(
  "R/00_config.R",
  "R/utils.R",
  "R/01_load_and_filter.R",
  "R/02_split_train_test.R",
  "R/03_predictor_screening.R",
  "R/04_null_model_icc.R",
  "R/05_mixed_models.R",
  "R/06_operational_model.R",
  "R/07_evaluate_test_set.R",
  "R/08_export_models.R"
)

for (s in steps) {
  cat("\n==============================", s, "==============================\n")
  source(s, echo = FALSE)
}
cat("\nDone. Models in outputs/models/, tables in outputs/tables/.\n")
