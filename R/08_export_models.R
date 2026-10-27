# =============================================================================
# 08_export_models.R — export every fitted model in machine-readable form
#   outputs/models/*.rds                 fitted R model objects
#   outputs/tables/fixed_effects_all_models.csv
#   outputs/tables/variance_components_all_models.csv
#   outputs/tables/station_coefficients_operational_model.csv
# =============================================================================

all_models <- list(model_ols = model_ols, model_1_null = model_1,
                   model_2_random_intercepts = model_2,
                   model_3_station_slope = model_3,
                   model_4_station_event_slopes = model_4,
                   model_5_operational = model_5)

for (n in names(all_models)) save_model(all_models[[n]], n)

fixed_all <- do.call(rbind, lapply(names(all_models), function(n)
  tidy_fixed(all_models[[n]], n)))
write_table(fixed_all, "fixed_effects_all_models")

mixed <- all_models[names(all_models) != "model_ols"]
vc_all <- do.call(rbind, lapply(names(mixed), function(n) tidy_varcomp(mixed[[n]], n)))
write_table(vc_all, "variance_components_all_models")

write_table(station_coefficients, "station_coefficients_operational_model")

# Session information for reproducibility
writeLines(utils::capture.output(utils::sessionInfo()),
           file.path(cfg$dir_models, "sessionInfo.txt"))
