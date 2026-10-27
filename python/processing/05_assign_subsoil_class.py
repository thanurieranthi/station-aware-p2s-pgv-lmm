import pandas as pd
from obspy.clients.fdsn import Client

# 1. Load your metadata
input_file = "metadata.csv"
try:
    df = pd.read_csv(input_file)
except FileNotFoundError:
    print(f"Error: Could not find {input_file}. Please ensure it is in the same directory.")
    exit()

# 2. Extract unique stations to minimize API calls
unique_stations = df['station'].dropna().unique()
print(f"Found {len(unique_stations)} unique stations. Fetching coordinates from GeoNet...")

# Initialize the GeoNet FDSN client
geonet_client = Client("GEONET")
station_coords = {}

for sta in unique_stations:
    try:
        # Fetch station level metadata for the NZ network
        inventory = geonet_client.get_stations(network="NZ", station=sta, level="station")
        if inventory and inventory[0].stations:
            lat = inventory[0].stations[0].latitude
            lon = inventory[0].stations[0].longitude
            station_coords[sta] = {'latitude': lat, 'longitude': lon}
        else:
            station_coords[sta] = {'latitude': None, 'longitude': None}
    except Exception as e:
        station_coords[sta] = {'latitude': None, 'longitude': None}

# Create a DataFrame of our unique station coordinates
coords_df = pd.DataFrame.from_dict(station_coords, orient='index').reset_index()
coords_df.rename(columns={'index': 'station'}, inplace=True)

# 3. Read the local site classes CSV
local_site_file = "nz_site_class.csv"
print(f"Reading local site classifications from {local_site_file}...")

try:
    # Read the local CSV
    site_class_df = pd.read_csv(local_site_file)
    
    # Strip any potential leading/trailing whitespace from column names just in case
    site_class_df.columns = site_class_df.columns.str.strip()
    
    # Check if the expected columns exist
    if 'Station' in site_class_df.columns and 'Site Class' in site_class_df.columns:
        # Keep only the necessary columns
        site_class_df = site_class_df[['Station', 'Site Class']].copy()
        
        # Rename them to match the desired output format
        site_class_df.rename(columns={
            'Station': 'station',
            'Site Class': 'nzs1170_5_2004_class'
        }, inplace=True)
        
        # Strip whitespace from the station column to ensure clean merging
        site_class_df['station'] = site_class_df['station'].astype(str).str.strip()
        site_class_df['nzs1170_5_2004_class'] = site_class_df['nzs1170_5_2004_class'].astype(str).str.strip()
        
    else:
        print(f"Error: Could not find 'Station' and 'Site Class' columns in {local_site_file}.")
        print(f"Available columns: {list(site_class_df.columns)}")
        site_class_df = pd.DataFrame(columns=['station', 'nzs1170_5_2004_class'])
        
except FileNotFoundError:
    print(f"Warning: Could not find {local_site_file}. Make sure it is in the same directory.")
    site_class_df = pd.DataFrame(columns=['station', 'nzs1170_5_2004_class'])
except Exception as e:
    print(f"An error occurred while reading the local CSV: {e}")
    site_class_df = pd.DataFrame(columns=['station', 'nzs1170_5_2004_class'])

# 4. Merge coordinates and Subsoil Classes back to the unique stations
coords_with_class = pd.merge(coords_df, site_class_df, on='station', how='left')

# 5. Merge back to the original large dataset
final_df = pd.merge(df, coords_with_class, on='station', how='left')

# Check how many were successfully matched
missing_classes = final_df['nzs1170_5_2004_class'].isna().sum()
total_records = len(final_df)
matched_records = total_records - missing_classes

print(f"\n--- Summary ---")
print(f"Total records: {total_records}")
print(f"Successfully assigned Subsoil Class: {matched_records}")
print(f"Missing Subsoil Class: {missing_classes}")

# Save the updated dataset
output_file = "metadata_with_subsoil_classes.csv"
final_df.to_csv(output_file, index=False)
print(f"Process complete. Data saved to {output_file}")