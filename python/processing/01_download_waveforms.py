# This function downloads the acceleration, velocity and displacement data
# directly from the strong motion sensor network (GeoNet) and stores each in
# its own HDF5 file. The raw waveform is downloaded only ONCE per trace;
# response removal is then performed three times (ACC/VEL/DISP) on copies of
# that same raw stream. The function reads metadata from an existing
# metadata.csv file.

import h5py
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
import csv
import numpy as np
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

OUTPUTS = ["ACC", "VEL", "DISP"]


def _resolve_path(path_value):
    path = Path(path_value)
    if path.is_absolute():
        return path

    if path.parts and path.parts[0] == BASE_DIR.name:
        return BASE_DIR.parent / path

    return BASE_DIR / path


def download_data(csv_file_path='support_complete_metadata.csv'):
    c = Client("GEONET")
    network = "NZ"
    location = "*"
    channel = "?N?"  # or "HHZ", "??E", "*N" etc.
    pre_filt = [0.05, 0.1, 40.0, 45.0]

    csv_file_path = _resolve_path(csv_file_path)

    hdf5_paths = {
        "ACC": _resolve_path('waveforms_acc.hdf5'),
        "VEL": _resolve_path('waveforms_vel.hdf5'),
        "DISP": _resolve_path('waveforms_disp.hdf5'),
    }
    for p in hdf5_paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)

    counts = {k: 0 for k in OUTPUTS}
    count_traces = 0
    count_skipped_time = 0

    hdf5_files = {k: h5py.File(p, 'w') for k, p in hdf5_paths.items()}
    data_groups = {k: hdf5_files[k].create_group("data") for k in OUTPUTS}

    try:
        with open(csv_file_path, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            for line in csv_reader:
                try:
                    station_code = line["station"]
                    trace_name = line["trace_name"]
                    reported_p_time = line["new_p_arrival_time"]
                    reported_s_time = line["new_s_arrival_time"]
                    magnitude = float(line["magnitude"])
                    epicentral_distance = float(line["epicentral_distance"])
                    event_type = line["event_type"]
                    magnitude_type = line["magnitude_type"]
                    trace_starttime = line["trace_starttime"]

                    print(f"Processing count: {count_traces}, Trace: {trace_name}")
                    count_traces += 1

                    # Filter: Skip if both reported_p_time and reported_s_time are not available
                    if not reported_p_time and not reported_s_time:
                        continue

                    picker = None
                    if reported_p_time:
                        picker = "P"
                    elif reported_s_time:
                        picker = "S"

                    starttime = UTCDateTime(trace_starttime)
                    endtime = UTCDateTime(trace_starttime) + 90

                    if magnitude < 3:
                        continue

                    if epicentral_distance > 150:
                        continue

                    if magnitude < 5.0 and epicentral_distance > 100:
                        continue

                    if event_type != "earthquake":
                        continue

                    # ---- Download the raw waveform ONCE ----
                    try:
                        raw_st = c.get_waveforms(network=network, station=station_code,
                                                  location=location, channel=channel,
                                                  starttime=starttime, endtime=endtime,
                                                  attach_response=True)
                    except Exception as e:
                        print(f"Error downloading trace {trace_name}: {e}")
                        continue

                    raw_st.detrend("demean")
                    raw_st.detrend("linear")
                    raw_st.taper(max_percentage=0.05, type='cosine')

                    # Check if the signal has exactly 3 traces (structural check,
                    # independent of ACC/VEL/DISP, so only needs to be done once)
                    if len(raw_st) < 3:
                        print(f"Skipping {trace_name} as it does not have 3 traces.")
                        continue

                    if len(raw_st) > 3:
                        # choose corequired channels here
                        selected = raw_st.select(channel="HN*")
                        if not selected:
                            selected = raw_st.select(channel="BN*")

                        if len(selected) != 3:
                            print(f"Skipping {trace_name} as it does not have 3 traces after channel selection.")
                            continue
                        raw_st = selected

                    new_p_arrival_sample = line.get("new_p_arrival_sample", "")
                    new_s_arrival_sample = line.get("new_s_arrival_sample", "")

                    # ---- Remove response separately for each output type ----
                    for output_i in OUTPUTS:
                        try:
                            st = raw_st.copy()
                            st.remove_response(output=output_i, pre_filt=pre_filt, water_level=60)
                            st.trim(starttime=starttime, endtime=endtime)

                            # Check the sampling rate / starttime alignment
                            actual_sr = st[0].stats.sampling_rate
                            actual_start = st[0].stats.starttime
                            dt = 1.0 / actual_sr
                            if abs(starttime - actual_start) > (dt / 2.0):
                                print(f"Skipping {trace_name} ({output_i}): starttime misaligned by "
                                      f"{abs(starttime - actual_start):.4f}s")
                                if output_i == "ACC":
                                    count_skipped_time += 1
                                continue

                            if len(st) != 3:
                                print(f"Skipping {trace_name} ({output_i}): does not have 3 traces after processing.")
                                continue

                            # Calculate p_arrival_sample and s_arrival_sample
                            p_arrival_sample = ""
                            s_arrival_sample = ""

                            if reported_p_time:
                                try:
                                    p_arrival_time_obj = UTCDateTime(reported_p_time)
                                    p_arrival_sample = int((p_arrival_time_obj - starttime) * actual_sr)
                                except Exception:
                                    p_arrival_sample = ""

                            if reported_s_time:
                                try:
                                    s_arrival_time_obj = UTCDateTime(reported_s_time)
                                    s_arrival_sample = int((s_arrival_time_obj - starttime) * actual_sr)
                                except Exception:
                                    s_arrival_sample = ""

                            # Combine all three traces into a single array
                            combined_data = np.stack([tr.data.astype(np.float32) for tr in st])

                            # Use trace_name as the key
                            dataset_name = f"{trace_name}"
                            dataset = data_groups[output_i].create_dataset(
                                dataset_name, data=combined_data, compression="gzip"
                            )

                            # Add metadata as attributes
                            dataset.attrs["trace_starttime"] = str(starttime)
                            dataset.attrs["magnitude"] = magnitude
                            dataset.attrs["epicentral_distance"] = epicentral_distance
                            dataset.attrs["event_type"] = event_type
                            dataset.attrs["channels"] = ",".join([tr.stats.channel for tr in st])
                            dataset.attrs["sampling_rate"] = actual_sr
                            dataset.attrs["network"] = st[0].stats.network
                            dataset.attrs["station"] = st[0].stats.station
                            dataset.attrs["p_arrival_time"] = str(reported_p_time)
                            dataset.attrs["p_arrival_sample"] = p_arrival_sample
                            dataset.attrs["s_arrival_time"] = str(reported_s_time)
                            dataset.attrs["s_arrival_sample"] = s_arrival_sample
                            dataset.attrs["new_p_arrival_sample"] = new_p_arrival_sample
                            dataset.attrs["new_s_arrival_sample"] = new_s_arrival_sample
                            dataset.attrs["picker"] = picker
                            dataset.attrs["magnitude_type"] = magnitude_type

                            counts[output_i] += 1

                        except Exception as e:
                            print(f"Error processing trace {trace_name} ({output_i}): {e}")
                            continue

                except Exception as e:
                    print(f"Error processing line: {line}, Error: {e}")
                    continue
    finally:
        for f in hdf5_files.values():
            f.close()

    print(f"Completed: ACC={counts['ACC']}, VEL={counts['VEL']}, DISP={counts['DISP']}")
    print(f"Skipped due to starttime mismatch (checked on ACC pass) = {count_skipped_time}")

    return hdf5_paths


def create_metadata(hdf5_file_path, metadata_csv_path):
    """Write a metadata CSV for a single HDF5 file (call once per ACC/VEL/DISP file)."""
    hdf5_file_path = _resolve_path(hdf5_file_path)
    metadata_csv_path = _resolve_path(metadata_csv_path)

    with h5py.File(hdf5_file_path, 'r') as hdf5_file:
        data_group = hdf5_file["data"]

        if len(data_group) == 0:
            print(f"No datasets found in {hdf5_file_path}, skipping metadata generation.")
            return

        # Get attribute keys from the first dataset
        first_dataset = next(iter(data_group.values()))
        attribute_keys = list(first_dataset.attrs.keys())
        attribute_keys.insert(0, "trace_name")  # Add trace_name as the first column

        with open(metadata_csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(attribute_keys)
            for dataset_name, dataset in data_group.items():
                row = [dataset_name] + [dataset.attrs.get(key, "") for key in attribute_keys[1:]]
                writer.writerow(row)

    print(f"Metadata written to {metadata_csv_path}")


if __name__ == "__main__":
    hdf5_paths = download_data()

    create_metadata(hdf5_paths["ACC"], _resolve_path("metadata_acc.csv"))
    create_metadata(hdf5_paths["VEL"], _resolve_path("metadata_vel.csv"))
    create_metadata(hdf5_paths["DISP"], _resolve_path("metadata_disp.csv"))