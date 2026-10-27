# Data dictionary — `data/raw/metadata_log10_cm.csv`

One row per station–event record (68,444 rows before selection). Amplitudes are log10 of values in
cm/s² (acceleration), cm/s (velocity), cm (displacement); `_1`, `_2`, `_3` = 1-, 2-, 3-s windows after the P pick.

| Column | Description |
|---|---|
| `EarthquakeKey` | record ID: `<EarthquakeID>_<StationName>` |
| `EarthquakeID` | GeoNet public event ID |
| `Year_Index` | calendar year of the event |
| `StationName` | GeoNet station code |
| `magnitude`, `magnitude_type`, `event_depth` | catalogue magnitude, type, depth (km) |
| `epicentral_distance`, `hypocentral_distance` | km |
| `channels`, `sampling_rate`, `trace_starttime` | waveform metadata (90-s window, P at ~30 s) |
| `new_p_arrival_sample`, `new_p_arrival_time` | PhaseNet P pick used for the feature windows |
| `pre_rmse_filter` | QC flag (1 = passed pre-event/signal RMS screening) |
| `log_Pa_t`, `log_Pv_t`, `log_Pd_t` | peak vertical P-wave acceleration / velocity / displacement |
| `log_IV2_t` | integral of squared vertical velocity (Suppl. Eq. S1) |
| `log_CAV_t` | cumulative absolute velocity, P window (Suppl. Eq. S3) |
| `log_tau_c_t` | characteristic period τc (Suppl. Eq. S2) |
| `log_PGA`, `log_PGV`, `log_PGD` | RotD50 horizontal peaks from P arrival to end of window |
| `SiteClass` | NZS 1170.5 subsoil class (A–E; empty = not assigned) |
| `Magnitude_Bin`, `Hypocentral_Distance_Bin` | bins used for plotting |
