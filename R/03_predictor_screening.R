# =============================================================================
# 03_predictor_screening.R — single-predictor OLS for the 18 candidate
# P-wave parameters (Pv, Pa, Pd, IV2, CAV, tau_c at 1, 2, 3 s); training data.
# Reproduces Supplementary Table S1.
# =============================================================================

candidates <- c(
  paste0("log_Pv_", 1:3), paste0("log_Pa_", 1:3), paste0("log_Pd_", 1:3),
  paste0("log_IV2_", 1:3), paste0("log_CAV_", 1:3), paste0("log_tau_c_", 1:3)
)

ols_models <- lapply(candidates, function(x) {
  stats::lm(stats::as.formula(paste(cfg$response, "~", x)), data = train_data)
})
names(ols_models) <- candidates

screening <- do.call(rbind, lapply(names(ols_models), function(x) {
  mod <- ols_models[[x]]
  actual <- mod$model[[1]]
  data.frame(
    predictor = x,
    R_squared = summary(mod)$r.squared,
    AIC  = stats::AIC(mod),
    BIC  = stats::BIC(mod),
    RMSE = sqrt(mean(mod$residuals^2)),
    MAPE = mean(abs(mod$residuals / actual)) * 100
  )
}))
print(screening, digits = 4)
write_table(screening, "table_S1_predictor_screening")

# Baseline model used throughout ("Model OLS", Eq. 7)
model_ols <- ols_models[[cfg$predictor]]
