# =============================================================================
# 05_mixed_models.R — candidate mixed-effects models (ML, bobyqa)
#   Model 2 (Eq. 8):  random intercepts
#   Model 3 (Eq. 9):  + station random slope         (selected model)
#   Model 4 (Eq. 10): + event random slope
# =============================================================================

model_2 <- lme4::lmer(
  log_PGV ~ 1 + log_IV2_3 + (1 | StationName) + (1 | EarthquakeID) +
    (1 | SiteClass) + (1 | Year_Index),
  data = train_data, REML = FALSE, control = cfg$lmer_control
)

model_3 <- lme4::lmer(
  log_PGV ~ 1 + log_IV2_3 + (1 + log_IV2_3 | StationName) + (1 | EarthquakeID) +
    (1 | SiteClass) + (1 | Year_Index),
  data = train_data, REML = FALSE, control = cfg$lmer_control
)

model_4 <- lme4::lmer(
  log_PGV ~ 1 + log_IV2_3 + (1 + log_IV2_3 | StationName) + (1 + log_IV2_3 | EarthquakeID) +
    (1 | SiteClass) + (1 | Year_Index),
  data = train_data, REML = FALSE, control = cfg$lmer_control
)

lrt <- stats::anova(model_1, model_2, model_3, model_4)
print(lrt)

r2 <- lapply(list(model_1 = model_1, model_2 = model_2, model_3 = model_3, model_4 = model_4),
             function(m) performance::r2(m, tolerance = 0))

model_comparison <- data.frame(
  model   = c("Model 1", "Model 2", "Model 3", "Model 4"),
  AIC     = lrt$AIC,
  BIC     = lrt$BIC,
  logLik  = lrt$logLik,
  chisq   = lrt$Chisq,
  df      = lrt$Df,
  p_value = lrt$`Pr(>Chisq)`,
  R2_conditional = sapply(r2, function(x) unname(x$R2_conditional)),
  R2_marginal    = sapply(r2, function(x) unname(x$R2_marginal)),
  row.names = NULL
)
print(model_comparison, digits = 6)
write_table(model_comparison, "table_2_model_comparison")
