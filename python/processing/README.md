# Waveform processing (Python)

Scripts used to build the record-level feature table from GeoNet strong-motion data.
Run in order; each script's CONFIG block/paths may need adjusting to your local layout.

| Step | Script | Purpose |
|---|---|---|
| 1 | `01_download_waveforms.py` | FDSN download of 90-s windows (30 s pre-P, 60 s post-P); demean, detrend, cosine taper; instrument response removal to acceleration, velocity and displacement (ObsPy `remove_response`, `pre_filt = [0.05, 0.1, 40, 45]` Hz, `water_level = 60`); HDF5 output |
| 2 | `02_qc_waveforms.py` | QC: pre-event/post-P RMS ratio and Welch low-frequency (< 0.15 Hz) energy fraction |
| 3 | `03_compute_peak_metrics.py` | Pa, Pv, Pd (vertical, 1–3 s) and RotD50 PGA/PGV/PGD |
| 4 | `04_compute_pwave_params.py` | IV2, τc, CAV (trapezoidal rule) and hypocentral distance |
| 5 | `05_assign_subsoil_class.py` | NZS 1170.5 subsoil class per station |
| 6 | `06_fetch_epicentres.py` | event coordinates for mapping |

P-wave arrivals were picked with PhaseNet (Zhu & Beroza, 2019); the picking step is not included here.

Requirements: see `requirements.txt`.
