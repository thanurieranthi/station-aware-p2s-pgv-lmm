"""
compute_pwave_params_and_hypo_distance.py

Adds nine columns to metadata.csv: tau_c, IV2, and CAV are each computed
for the initial 1-, 2-, and 3-second P-wave windows
(new_p_arrival_sample to +Ns) of the VERTICAL channel:

  tau_c  : predominant period parameter (Wu & Kanamori-style on-site EEW
           parameter), computed from vertical DISPLACEMENT and VELOCITY:

            tau_c_N = 2*pi * sqrt( integral(d(t)^2 dt) / integral(v(t)^2 dt) )

           where d(t) is vertical displacement and v(t) = d-dot(t) is
           vertical velocity, both integrated over the first 3 seconds
           after the P arrival. tau_c scales with earthquake size because
           larger ruptures radiate more long-period energy in even the
           earliest part of the P wave. The saved value is log10(tau_c).

  IV2    : integral of squared vertical velocity over the same window,
           i.e. the denominator of tau_c reported as its own amplitude-
           type parameter:

               IV2 = integral(v(t)^2 dt)


  CAV    : Cumulative Absolute Velocity computed on vertical ACCELERATION
           over the same window (the general engineering CAV integrates
           |a(t)| over the whole record; here it's restricted to the
           P-wave window to match tau_c/IV2, consistent with its use as
           an on-site EEW feature rather than a full-record damage index):

               CAV = integral(|a(t)| dt)


All three P-wave parameters use the VERTICAL channel (identified from the
"channels" column, same convention as the earlier scripts: a code ending
in "Z" is vertical). This matches how these on-site EEW parameters are
conventionally computed, since the vertical component is typically used
for continuous real-time triggering/processing. If your reference
defines any of these differently (e.g. horizontal component, a different
           window lengths), the CONFIG section below is the place to change it.

Integration is done with the trapezoidal rule (numpy.trapz).

Requires: h5py, numpy, obspy (for the FDSN station lookup)

Edit CONFIG below, then run:
    python compute_pwave_params_and_hypo_distance.py

Note: this overwrites METADATA_FILE in place. Keep a backup if needed.
"""

import csv
import h5py
import numpy as np
from pathlib import Path
from obspy.clients.fdsn import Client

# numpy >= 2.0 renamed trapz -> trapezoid; support either version
_trapz = getattr(np, "trapezoid", None) or np.trapz


def _round_sig(val, sig_figs=6):
    """Rounds to a fixed number of SIGNIFICANT figures rather than decimal
    places. Fixed-decimal rounding (e.g. round(val, 6)) silently floors
    small-magnitude columns like IV2 (~1e-8 to 1e-9) to 0.0; significant-
    figure rounding preserves precision regardless of a value's scale."""
    if val == 0:
        return 0.0
    return float(f"{val:.{sig_figs}g}")

# ---- CONFIG -------------------------------------------------------------
HDF5_FILES = {
    "ACC": "waveforms_acc.hdf5",
    "VEL": "waveforms_vel.hdf5",
    "DISP": "waveforms_disp.hdf5",
}
METADATA_FILE = "metadata_log10_cm.csv"
P_WINDOW_SECS = (1.0, 2.0, 3.0)  # P-wave window durations to calculate
FDSN_PROVIDER = "GEONET"
DEFAULT_NETWORK = "NZ"      # used if a row has no "network" column
# --------------------------------------------------------------------------


def _to_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _log10_scaled(val, scale):
    if val is None or not np.isfinite(val) or val <= 0:
        return np.nan
    return float(np.log10(val * scale))


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


def window_slice(arr, start_idx, n_samples):
    if arr is None or start_idx is None or start_idx >= arr.shape[0]:
        return None
    end_idx = min(start_idx + n_samples, arr.shape[0])
    seg = arr[start_idx:end_idx]
    return seg if seg.size > 1 else None


def compute_pwave_params(disp_v, vel_v, acc_v, sampling_rate, p_idx,
                          window_sec=3.0):
    """Returns (tau_c, IV2, CAV) from the vertical DISP/VEL/ACC channels."""
    n_samples = int(round(sampling_rate * window_sec))
    dt = 1.0 / sampling_rate

    tau_c, iv2, cav = np.nan, np.nan, np.nan

    d_seg = window_slice(disp_v, p_idx, n_samples)
    v_seg = window_slice(vel_v, p_idx, n_samples)
    if d_seg is not None and v_seg is not None:
        int_d2 = _trapz(d_seg.astype(np.float64) ** 2, dx=dt)
        int_v2 = _trapz(v_seg.astype(np.float64) ** 2, dx=dt)
        iv2 = float(int_v2)
        if int_v2 > 0:
            tau_c = float(2 * np.pi * np.sqrt(int_d2 / int_v2))

    a_seg = window_slice(acc_v, p_idx, n_samples)
    if a_seg is not None:
        cav = float(_trapz(np.abs(a_seg.astype(np.float64)), dx=dt))

    return tau_c, iv2, cav


_station_elevation_cache = {}


def get_station_elevation_km(client, network, station):
    """Fetches station elevation (km, above sea level) from the FDSN
    station webservice, caching results per (network, station)."""
    key = (network, station)
    if key in _station_elevation_cache:
        return _station_elevation_cache[key]

    elev_km = None
    try:
        inv = client.get_stations(network=network, station=station, level="station")
        elev_m = inv[0][0].elevation
        elev_km = elev_m / 1000.0
    except Exception as e:
        print(f"  WARNING: could not fetch station coordinates for "
              f"{network}.{station}: {e}")

    _station_elevation_cache[key] = elev_km
    return elev_km


def compute_hypocentral_distance(epicentral_km, depth_km, elevation_km):
    if epicentral_km is None or depth_km is None:
        return np.nan
    vertical_sep = depth_km + (elevation_km if elevation_km is not None else 0.0)
    return float(np.sqrt(epicentral_km ** 2 + vertical_sep ** 2))


def main():
    metadata_path = Path(METADATA_FILE)
    with open(metadata_path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    parameter_columns = [
        f"{parameter}_{int(window_sec)}"
        for window_sec in P_WINDOW_SECS
        for parameter in ("tau_c", "IV2", "CAV")
    ]
    new_columns = parameter_columns
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)

    hdf5_handles = {}
    for label, path in HDF5_FILES.items():
        path = Path(path)
        if not path.exists():
            print(f"WARNING: {path} not found, {label}-derived values will be blank")
            hdf5_handles[label] = None
        else:
            hdf5_handles[label] = h5py.File(path, "r")

    # client = Client(FDSN_PROVIDER)

    try:
        for row in rows:
            trace_name = row["trace_name"]
            channels = [c.strip() for c in row.get("channels", "").split(",")]
            sampling_rate = _to_float(row.get("sampling_rate", "")) or 100.0
            p_idx = _to_int(row.get("new_p_arrival_sample", ""))

            vert_idx, horiz_idx = get_channel_indices(channels)

            disp_v = vel_v = acc_v = None
            if vert_idx is not None:
                for label, target in [("DISP", "disp_v"), ("VEL", "vel_v"), ("ACC", "acc_v")]:
                    f = hdf5_handles[label]
                    if f is not None and trace_name in f["data"]:
                        data = f["data"][trace_name][()]
                        if target == "disp_v":
                            disp_v = data[vert_idx]
                        elif target == "vel_v":
                            vel_v = data[vert_idx]
                        else:
                            acc_v = data[vert_idx]
            else:
                print(f"WARNING: {trace_name}: could not identify vertical channel "
                      f"from '{channels}'")

            parameter_values = {}
            for window_sec in P_WINDOW_SECS:
                tau_c, iv2, cav = compute_pwave_params(
                    disp_v, vel_v, acc_v, sampling_rate, p_idx, window_sec
                )
                parameter_values.update({
                    f"tau_c_{int(window_sec)}": _log10_scaled(tau_c, 1),
                    f"IV2_{int(window_sec)}": _log10_scaled(iv2, 10000),
                    f"CAV_{int(window_sec)}": _log10_scaled(cav, 100),
                })

            # station = row.get("station", "")
            # network = row.get("network", DEFAULT_NETWORK)
            # epicentral_km = _to_float(row.get("epicentral_distance", ""))
            # depth_km = _to_float(row.get("event_depth", ""))
            # elevation_km = get_station_elevation_km(client, network, station) if station else None
            # hyp_dist = compute_hypocentral_distance(epicentral_km, depth_km, elevation_km)

            values = parameter_values
            for col in new_columns:
                val = values[col]
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