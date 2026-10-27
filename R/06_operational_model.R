# =============================================================================
# 06_operational_model.R — operational EEW model (Model 5, Eq. 11):
#   log(PGV) = (b0 + u0s) + (b1 + u1s) * log(IV2)
# Only station-specific random intercepts and slopes are retained.
# =============================================================================

model_5 <- lme4::lmer(
  log_PGV ~ 1 + log_IV2_3 + (1 + log_IV2_3 | StationName),
  data = train_data, REML = FALSE, control = cfg$lmer_control
)
print(summary(model_5))

# Station-specific coefficients (Supplementary Table S5)
fe <- lme4::fixef(model_5)
re <- lme4::ranef(model_5, condVar = TRUE)$StationName
post_var <- attr(re, "postVar")
n_train <- table(droplevels(train_data$StationName))
site_class <- tapply(as.character(train_data$SiteClass), train_data$StationName,
                     function(x) x[1])

station_coefficients <- data.frame(
  station           = rownames(re),
  nzs1170_5_class   = unname(site_class[rownames(re)]),
  n_train_records   = as.integer(n_train[rownames(re)]),
  u0s               = re[, "(Intercept)"],
  u1s               = re[, "log_IV2_3"],
  u0s_cond_sd       = sqrt(post_var[1, 1, ]),
  u1s_cond_sd       = sqrt(post_var[2, 2, ]),
  final_intercept   = fe[["(Intercept)"]] + re[, "(Intercept)"],
  final_slope       = fe[["log_IV2_3"]]   + re[, "log_IV2_3"],
  row.names = NULL
)
