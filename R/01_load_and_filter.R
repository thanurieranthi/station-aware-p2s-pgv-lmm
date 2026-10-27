# =============================================================================
# 01_load_and_filter.R — read the feature table and apply record selection
#   * QC flag (pre-event / signal RMS screening)
#   * remove records with 3-s Pv >= PGV
#   * events up to cfg$max_year
#   * stations with >= cfg$min_records_station records
# =============================================================================

log_step("Loading ", cfg$data_file)
eqdata <- utils::read.csv(cfg$data_file, check.names = FALSE)
n_raw <- nrow(eqdata)

eqdata <- dplyr::filter(eqdata, pre_rmse_filter == 1)
n_qc <- nrow(eqdata)

eqdata <- eqdata |>
  dplyr::filter(!is.na(log_Pv_3) & !is.na(log_PGV)) |>
  dplyr::filter(log_Pv_3 < log_PGV)
n_pv <- nrow(eqdata)

eqdata <- eqdata[eqdata$Year_Index <= cfg$max_year, ]

eqdata <- eqdata |>
  dplyr::group_by(StationName) |>
  dplyr::filter(dplyr::n() >= cfg$min_records_station) |>
  dplyr::ungroup()

factor_cols <- c("EarthquakeID", "EarthquakeKey", "StationName", "SiteClass",
                 "Year_Index", "Magnitude_Bin", "Hypocentral_Distance_Bin")
for (v in factor_cols) eqdata[[v]] <- factor(eqdata[[v]])

selection_log <- data.frame(
  step = c("raw", "QC flag", "Pv < PGV", "year + station filters"),
  records = c(n_raw, n_qc, n_pv, nrow(eqdata))
)
print(selection_log)
log_step(nrow(eqdata), " records | ", nlevels(eqdata$EarthquakeID), " events | ",
         nlevels(eqdata$StationName), " stations")
