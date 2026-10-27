"""
find_corrupted_traces.py

Scans the traces listed in a single metadata.csv (attributes are shared
across ACC/VEL/DISP, so one file covers all three) and reports which
trace_names look corrupted in each of the ACC/VEL/DISP HDF5 files.
Read-only: does not modify or create any file.

Driving the scan from metadata.csv instead of the HDF5 dataset list means
you control exactly which traces get checked: edit/filter rows in the
metadata CSV (keep only a subset, drop ones you've already handled, etc.)
before running this script. The metadata CSV supplies the trace_name
list plus the new_p_arrival_sample / sampling_rate attributes; the
actual waveform samples used for the QC metrics still come from the
HDF5 files, since metadata.csv doesn't store amplitude values.

Two independent metrics are checked, either of which can flag a trace:

1. Pre-event vs signal RMS ratio
   Real strong-motion noise before the P arrival should be small compared
   to the shaking. If the "quiet" part of the trace is comparable to (or
   larger than) the signal, the deconvolution/integration is unstable.
   Falls back to using the first 10% of the trace as "noise" if
   new_p_arrival_sample isn't available in the CSV for that row.

2. Low-frequency power fraction
   Deconvolution/integration artifacts concentrate energy at very low
   frequencies (below the pre_filt corner used in remove_response).
   This metric doesn't need a P pick, so it acts as a backup.

Edit CONFIG below to point at your file paths, then run:
    python find_corrupted_traces.py
"""

import csv
import h5py
import numpy as np
from pathlib import Path
from scipy.signal import welch

# ---- CONFIG -------------------------------------------------------------
HDF5_FILES = {
    "ACC": "waveforms_acc.hdf5",
    "VEL": "waveforms_vel.hdf5",
    "DISP": "waveforms_disp.hdf5",
}
METADATA_FILE = "metadata.csv"
CORNER_HZ = 0.15          # spectral check: frequencies below this = "low"
RMS_RATIO_THRESH = 0.7    # flag if pre-event RMS > 50% of signal RMS
LOW_FREQ_THRESH = 0.6     # flag if >60% of PSD energy is below CORNER_HZ
REPORT_PATH = "corrupted_traces_report.txt"
# --------------------------------------------------------------------------


def _to_int(val):
    try:
        v = int(float(val))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _to_float(val, default):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def read_trace_list(csv_path):
    """Reads trace_name + relevant attrs from the metadata CSV.
    Edit/filter this CSV to control which traces get scanned."""
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "trace_name": row["trace_name"],
                "p_arrival_sample": _to_int(row.get("new_p_arrival_sample", "")),
                "sampling_rate": _to_float(row.get("sampling_rate", ""), 100.0),
            })
    return rows


def _pre_post_rms_ratio(data, p_idx):
    n = data.shape[1]
    if p_idx is None or p_idx < 20 or p_idx > n - 20:
        p_idx = max(int(n * 0.1), 1)  # fallback: first 10% as "noise"
    noise = data[:, :p_idx]
    signal = data[:, p_idx:]
    noise_rms = np.sqrt(np.mean(noise ** 2, axis=1))
    signal_rms = np.sqrt(np.mean(signal ** 2, axis=1)) + 1e-12
    return float(np.max(noise_rms / signal_rms))  # worst of the 3 components


def _low_freq_fraction(data, sampling_rate, corner_hz):
    fracs = []
    for ch in data:
        nperseg = min(1024, len(ch))
        freqs, psd = welch(ch, fs=sampling_rate, nperseg=nperseg)
        low = psd[freqs < corner_hz].sum()
        total = psd.sum() + 1e-30
        fracs.append(low / total)
    return float(max(fracs))  # worst of the 3 components


def scan_output_type(label, trace_rows):
    """Returns {trace_name: {metric: value}} for traces (drawn from the
    shared metadata CSV) that fail QC when checked against this output
    type's HDF5 waveforms."""
    hdf5_path = Path(HDF5_FILES[label])
    if not hdf5_path.exists():
        print(f"Skipping {label}: {hdf5_path} not found")
        return {}

    flagged = {}
    with h5py.File(hdf5_path, "r") as f:
        group = f["data"]
        for row in trace_rows:
            name = row["trace_name"]
            if name not in group:
                print(f"  WARNING: {name} listed in {METADATA_FILE} but missing from {hdf5_path}")
                continue

            data = group[name][()].astype(np.float64)
            ratio = _pre_post_rms_ratio(data, row["p_arrival_sample"])
            low_frac = _low_freq_fraction(data, row["sampling_rate"], CORNER_HZ)

            if ratio > RMS_RATIO_THRESH or low_frac > LOW_FREQ_THRESH:
                flagged[name] = {
                    "pre_post_rms_ratio": round(ratio, 3),
                    "low_freq_fraction": round(low_frac, 3),
                }
    return flagged


def main():
    csv_path = Path(METADATA_FILE)
    if not csv_path.exists():
        print(f"Metadata file not found: {csv_path}")
        return

    trace_rows = read_trace_list(csv_path)
    print(f"Loaded {len(trace_rows)} trace(s) from {csv_path}")

    results = {}
    for label in HDF5_FILES:
        results[label] = scan_output_type(label, trace_rows)

    lines = []
    for label, flagged in results.items():
        names = sorted(flagged.keys())
        print(f"\n{label} -> {len(names)} suspect trace(s)")
        lines.append(f"{label} -> {names}")
        for name in names:
            m = flagged[name]
            detail = (f"    {name}: pre_post_rms_ratio={m['pre_post_rms_ratio']}, "
                      f"low_freq_fraction={m['low_freq_fraction']}")
            print(detail)
            lines.append(detail)

    Path(REPORT_PATH).write_text("\n".join(lines))
    print(f"\nReport written to {REPORT_PATH}")


if __name__ == "__main__":
    main()