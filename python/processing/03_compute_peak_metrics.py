"""
compute_peak_metrics.py

Computes P-wave-window vertical peak metrics (Pa-1/2/3, Pv-1/2/3, Pd-1/2/3)
and full-waveform horizontal peak-ground metrics (PGA, PGV, PGD) for every
trace listed in metadata.csv, and appends them as new columns.

- ACC-related metrics (Pa-1/2/3, PGA) are computed from waveforms_acc.hdf5
- VEL-related metrics (Pv-1/2/3, PGV) are computed from waveforms_vel.hdf5
- DISP-related metrics (Pd-1/2/3, PGD) are computed from waveforms_disp.hdf5

Definitions:
  Pa-N / Pv-N / Pd-N : peak ABSOLUTE value of the VERTICAL channel over the
                        first N second(s) after new_p_arrival_sample.
  PGA / PGV / PGD     : peak HORIZONTAL value (RotD50) over the segment from
                        new_p_arrival_sample to the end of the waveform.

RotD50 (Boore, 2010): the two horizontal components are jointly rotated
through 0-179 degrees (1-degree steps); at each angle the peak absolute
value of the rotated horizontal trace is taken; RotD50 is the median of
those peak values across all angles.

Vertical/horizontal channels are identified from the "channels" column:
a channel ending in "Z" is treated as vertical, the other two as horizontal.

Edit CONFIG below, then run:
    python compute_peak_metrics.py

Note: this overwrites METADATA_FILE in place. Keep a backup if needed.
"""

import csv
import h5py
import numpy as np
from pathlib import Path

# ---- CONFIG -------------------------------------------------------------
HDF5_FILES = {
    "ACC": "waveforms_acc.hdf5",
    "VEL": "waveforms_vel.hdf5",
    "DISP": "waveforms_disp.hdf5",
}
METADATA_FILE = "metadata.csv"
ROTD_ANGLES_DEG = np.arange(0, 180, 1)  # 1-degree steps, standard RotD50
P_WINDOWS_SEC = [1, 2, 3]
# --------------------------------------------------------------------------

_COS_A = np.cos(np.deg2rad(ROTD_ANGLES_DEG))
_SIN_A = np.sin(np.deg2rad(ROTD_ANGLES_DEG))


def _round_sig(val, sig_figs=6):
    """Rounds to a fixed number of SIGNIFICANT figures rather than decimal
    places. Fixed-decimal rounding (e.g. round(val, 6)) silently floors
    sub-micron displacement peaks (Pd-1/2/3) to 0.0; significant-figure
    rounding preserves precision regardless of a value's scale."""
    if val == 0:
        return 0.0
    return float(f"{val:.{sig_figs}g}")


def _to_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def get_channel_indices(channels):
    """Returns (vertical_index, [horizontal_index1, horizontal_index2])
    based on channel codes ending in 'Z' (vertical) vs not (horizontal)."""
    vert_idx = None
    horiz_idx = []
    for i, ch in enumerate(channels):
        if ch.strip().upper().endswith("Z"):
            vert_idx = i
        else:
            horiz_idx.append(i)
    return vert_idx, horiz_idx


def rotd50_peak(h1, h2):
    """RotD50 peak absolute value across the two horizontal components."""
    if h1.size == 0:
        return np.nan
    rotated = np.outer(_COS_A, h1) + np.outer(_SIN_A, h2)  # (n_angles, n_samples)
    peaks = np.max(np.abs(rotated), axis=1)                # (n_angles,)
    return float(np.median(peaks))


def vertical_peak(vert, start_idx, n_samples):
    """Peak absolute value of the vertical channel over
    [start_idx, start_idx + n_samples), clipped to what's available."""
    if start_idx is None or start_idx >= vert.shape[0]:
        return np.nan
    end_idx = min(start_idx + n_samples, vert.shape[0])
    segment = vert[start_idx:end_idx]
    if segment.size == 0:
        return np.nan
    return float(np.max(np.abs(segment)))


def compute_p_window_metrics(vert, sampling_rate, p_idx, prefix):
    result = {}
    for sec in P_WINDOWS_SEC:
        n_samples = int(round(sampling_rate * sec))
        result[f"{prefix}-{sec}"] = vertical_peak(vert, p_idx, n_samples)
    return result


def compute_pg_metric(h1, h2, p_idx):
    """RotD50 peak over [p_idx, end] for the horizontal pair."""
    if p_idx is None or p_idx >= h1.shape[0]:
        return np.nan
    return rotd50_peak(h1[p_idx:], h2[p_idx:])


def main():
    metadata_path = Path(METADATA_FILE)
    with open(metadata_path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    new_columns = ["Pa-1", "Pa-2", "Pa-3", "PGA",
                   "Pv-1", "Pv-2", "Pv-3", "PGV",
                   "Pd-1", "Pd-2", "Pd-3", "PGD"]
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)

    hdf5_handles = {}
    for label, path in HDF5_FILES.items():
        path = Path(path)
        if not path.exists():
            print(f"WARNING: {path} not found, {label} metrics will be blank for all traces")
            hdf5_handles[label] = None
        else:
            hdf5_handles[label] = h5py.File(path, "r")

    try:
        for row in rows:
            trace_name = row["trace_name"]
            channels = [c.strip() for c in row.get("channels", "").split(",")]
            sampling_rate = float(row.get("sampling_rate", 100.0))
            p_idx = _to_int(row.get("new_p_arrival_sample", ""))

            vert_idx, horiz_idx = get_channel_indices(channels)
            if vert_idx is None or len(horiz_idx) != 2:
                print(f"WARNING: {trace_name}: could not identify vertical/horizontal "
                      f"channels from '{channels}', leaving metrics blank")
                for col in new_columns:
                    row[col] = ""
                continue

            metrics = {}
            for label, prefix, pg_key in [("ACC", "Pa", "PGA"),
                                           ("VEL", "Pv", "PGV"),
                                           ("DISP", "Pd", "PGD")]:
                f = hdf5_handles[label]
                if f is None or trace_name not in f["data"]:
                    for sec in P_WINDOWS_SEC:
                        metrics[f"{prefix}-{sec}"] = np.nan
                    metrics[pg_key] = np.nan
                    continue

                data = f["data"][trace_name][()].astype(np.float64)
                vert = data[vert_idx]
                h1 = data[horiz_idx[0]]
                h2 = data[horiz_idx[1]]

                metrics.update(compute_p_window_metrics(vert, sampling_rate, p_idx, prefix))
                metrics[pg_key] = compute_pg_metric(h1, h2, p_idx)

            for col in new_columns:
                val = metrics.get(col, np.nan)
                row[col] = "" if (val is None or not np.isfinite(val)) else _round_sig(val)

            print(f"{trace_name}: " + ", ".join(f"{c}={row[c]}" for c in new_columns))

    finally:
        for f in hdf5_handles.values():
            if f is not None:
                f.close()

    with open(metadata_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nUpdated {metadata_path} with columns: {', '.join(new_columns)}")


if __name__ == "__main__":
    main()