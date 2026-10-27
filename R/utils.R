# =============================================================================
# utils.R — helper functions shared across the pipeline
# =============================================================================

log_step <- function(...) {
  cat(sprintf("[%s] ", format(Sys.time(), "%H:%M:%S")), ..., "\n", sep = "")
}

write_table <- function(df, name) {
  path <- file.path(cfg$dir_tables, paste0(name, ".csv"))
  utils::write.csv(df, path, row.names = FALSE)
  log_step("wrote ", path)
  invisible(path)
}

save_model <- function(model, name) {
  path <- file.path(cfg$dir_models, paste0(name, ".rds"))
  saveRDS(model, path)
  log_step("wrote ", path)
  invisible(path)
}

# Fixed effects (estimate, SE) for lm / lmerMod objects
tidy_fixed <- function(model, model_name) {
  cf <- summary(model)$coefficients
  data.frame(
    model    = model_name,
    term     = rownames(cf),
    estimate = unname(cf[, 1]),
    std_error = unname(cf[, 2]),
    row.names = NULL
  )
}

# Variance components (variances, SDs, correlations) for lmerMod objects
tidy_varcomp <- function(model, model_name) {
  vc <- as.data.frame(lme4::VarCorr(model))
  data.frame(
    model    = model_name,
    group    = vc$grp,
    term1    = vc$var1,
    term2    = vc$var2,
    variance_or_cov = vc$vcov,
    sd_or_cor = vc$sdcor,
    row.names = NULL
  )
}

# Test-set metrics as reported in the manuscript (Table 3).
# NOTE: MAPE follows the original analysis script (back-transform with exp()).
test_metrics_table3 <- function(model, newdata, model_name) {
  pred <- stats::predict(model, newdata = newdata, allow.new.levels = TRUE)
  obs  <- newdata[[cfg$response]]
  res  <- obs - pred
  data.frame(
    model = model_name,
    MSE   = mean(res^2),
    RMSE  = sqrt(mean(res^2)),
    MAPE  = mean(abs((exp(obs) - exp(pred)) / exp(obs))) * 100
  )
}
