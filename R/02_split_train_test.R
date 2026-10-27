# =============================================================================
# 02_split_train_test.R — event-based ~80:20 split
# Records from one earthquake are never shared between training and test.
# =============================================================================

unique_eq <- unique(eqdata$EarthquakeID)

set.seed(cfg$seed)
train_eq <- sample(unique_eq, size = round(cfg$train_fraction * length(unique_eq)))

train_data <- subset(eqdata, EarthquakeID %in% train_eq)
test_data  <- subset(eqdata, !(EarthquakeID %in% train_eq))
stopifnot(length(intersect(unique(train_data$EarthquakeID),
                           unique(test_data$EarthquakeID))) == 0)

# Force selected large events into the test set
for (ev in cfg$forced_test_events) {
  moved      <- subset(train_data, EarthquakeID == ev)
  test_data  <- rbind(test_data, moved)
  train_data <- subset(train_data, EarthquakeID != ev)
}

# Remove test-set outlier records
test_data <- subset(test_data, !(EarthquakeKey %in% cfg$test_outlier_keys))

utils::write.csv(train_data, file.path(cfg$dir_processed, "train_data_set.csv"), row.names = FALSE)
utils::write.csv(test_data,  file.path(cfg$dir_processed, "test_data_set.csv"),  row.names = FALSE)

log_step("train: ", nrow(train_data), " records / ", length(unique(train_data$EarthquakeID)), " events")
log_step("test:  ", nrow(test_data),  " records / ", length(unique(test_data$EarthquakeID)),  " events")
