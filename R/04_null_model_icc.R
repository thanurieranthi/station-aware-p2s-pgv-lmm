# =============================================================================
# 04_null_model_icc.R — unconditional means model (Model 1) with crossed
# random intercepts; ICC (Suppl. Eq. S4) and design effect (Suppl. Eq. S5).
# =============================================================================

model_1 <- lme4::lmer(
  log_PGV ~ 1 + (1 | SiteClass) + (1 | StationName) + (1 | EarthquakeID) + (1 | Year_Index),
  data = train_data, REML = FALSE, control = cfg$lmer_control
)

vc <- as.data.frame(lme4::VarCorr(model_1))
var_resid <- attr(lme4::VarCorr(model_1), "sc")^2
groups <- c(StationName = "Station", SiteClass = "Subsoil class",
            EarthquakeID = "Earthquake event", Year_Index = "Calendar year")

icc_table <- do.call(rbind, lapply(names(groups), function(g) {
  v_g  <- vc$vcov[vc$grp == g]
  icc  <- v_g / (v_g + var_resid)                          # Eq. S4
  m_bar <- mean(tapply(eqdata$log_PGV, eqdata[[g]], length))
  data.frame(
    grouping_factor = groups[[g]],
    variance = v_g,
    ICC = icc,
    mean_cluster_size = m_bar,
    design_effect = 1 + (m_bar - 1) * icc                  # Eq. S5
  )
}))
print(icc_table, digits = 4)
write_table(icc_table, "table_1_icc_design_effect")
