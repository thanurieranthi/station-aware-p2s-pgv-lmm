# =============================================================================
# 00_config.R — project-wide settings
# All paths are relative to the repository root (run scripts from there).
# =============================================================================

cfg <- list(
  data_file      = file.path("data", "raw", "metadata_log10_cm.csv"),
  dir_processed  = file.path("data", "processed"),
  dir_models     = file.path("outputs", "models"),
  dir_tables     = file.path("outputs", "tables"),

  # --- record selection --------------------------------------------------
  max_year            = 2022,   # keep events up to and including 2022
  min_records_station = 5,      # stations with >= 5 qualifying records

  # --- event-based train/test split -------------------------------------
  seed           = 47,
  train_fraction = 0.8,
  forced_test_events = c("2016p858000"),  # 2016 M7.8 Kaikoura

  # Test-set records excluded as outliers (EarthquakeKey = EventID_Station)
  test_outlier_keys = c(
    "2016p858094_HSES", "2016p862338_BWRS", "2016p858013_AMBC",
    "2013p613797_NWFS", "2018p248771_RPZ",  "2013p613797_NBSS",
    "2013p542863_POKS"
  ),

  # --- modelling -------------------------------------------------------
  response  = "log_PGV",
  predictor = "log_IV2_3",        # 3-s squared-velocity integral (log10)
  lmer_control = lme4::lmerControl(optimizer = "bobyqa")
)

for (d in c(cfg$dir_processed, cfg$dir_models, cfg$dir_tables)) {
  dir.create(d, recursive = TRUE, showWarnings = FALSE)
}
