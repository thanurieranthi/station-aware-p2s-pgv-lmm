# =============================================================================
# 07_evaluate_test_set.R — out-of-sample evaluation on the independent test set
# Random effects for levels absent from training (e.g. new events) are set to 0
# (lme4 allow.new.levels = TRUE).
# =============================================================================

eval_models <- list("Model OLS" = model_ols, "Model 1" = model_1, "Model 2" = model_2,
                    "Model 3" = model_3, "Model 4" = model_4, "Model 5" = model_5)

table3 <- do.call(rbind, lapply(names(eval_models), function(n)
  test_metrics_table3(eval_models[[n]], test_data, n)))
table3$RMSE_reduction_vs_OLS_pct <- 100 * (table3$RMSE[1] - table3$RMSE) / table3$RMSE[1]
print(table3, digits = 6)
write_table(table3, "table_3_test_metrics")

# Operational model (Model 5) summary metrics, as reported in the text
obs  <- test_data$log_PGV
p5   <- stats::predict(model_5, newdata = test_data, allow.new.levels = TRUE)
pols <- stats::predict(model_ols, newdata = test_data)
operational_metrics <- data.frame(
  model = c("Model 5", "Model OLS"),
  n     = length(obs),
  RMSE  = c(sqrt(mean((obs - p5)^2)), sqrt(mean((obs - pols)^2))),
  MAE   = c(mean(abs(obs - p5)), mean(abs(obs - pols))),
  bias  = c(mean(obs - p5), mean(obs - pols)),
  R2_cor_squared = c(stats::cor(obs, p5)^2, stats::cor(obs, pols)^2),
  R2_one_minus_rss_tss = c(1 - sum((obs - p5)^2)   / sum((obs - mean(obs))^2),
                           1 - sum((obs - pols)^2) / sum((obs - mean(obs))^2))
)
print(operational_metrics, digits = 6)
write_table(operational_metrics, "operational_model_test_metrics")

# Per-station test RMSE (Figure 7)
station_test_metrics <- data.frame(station = test_data$StationName, res = obs - p5) |>
  dplyr::group_by(station) |>
  dplyr::summarise(n_test = dplyr::n(), mean_residual = mean(res),
                   sd_residual = stats::sd(res), RMSE = sqrt(mean(res^2)), .groups = "drop")
write_table(station_test_metrics, "station_test_metrics")
