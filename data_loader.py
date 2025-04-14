import os
import time
import csv
import pandas as pd
import sqlite3
from concurrent.futures import ThreadPoolExecutor

# Import geopy for geocoding (currently not used due to commenting out)
try:
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="physician_compare_geocoder", timeout=10)
except ImportError:
    geolocator = None

# -------------------- Utility Functions --------------------

def normalize_phone(phone: str) -> str:
    """Normalize phone numbers to the format (xxx) xxx-xxxx."""
    if not phone or pd.isna(phone):
        return None
    digits = "".join(filter(str.isdigit, str(phone)))
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return digits if digits else None

def format_address(line1: str, line2: str, city: str, state: str, zip_code: str, line2_suppression: str = None) -> str:
    """Combine address parts into a single string for geocoding."""
    parts = []
    if line1 and not pd.isna(line1):
        parts.append(str(line1).strip())
    if line2 and not pd.isna(line2):
        if line2_suppression and str(line2_suppression).strip().upper() == 'Y':
            pass
        else:
            parts.append(str(line2).strip())
    if city and not pd.isna(city):
        parts.append(str(city).strip())
    if state and not pd.isna(state):
        parts.append(str(state).strip())
    if zip_code and not pd.isna(zip_code):
        parts.append(str(zip_code).strip())
    return ", ".join(parts)

# -------------------- Geocoding Functions --------------------
# The following geocoding function and related code have been commented out to avoid
# API rate limits and connection timeouts. The latitude and longitude fields will be set to None.

# def geocode_address(address: str):
#     """
#     Geocode a full address string using Nominatim.
#     Returns a tuple (address, latitude, longitude). If unsuccessful, returns (address, None, None).
#     """
#     if geolocator is None:
#         return address, None, None
#     try:
#         location = geolocator.geocode(address)
#         if location:
#             return address, location.latitude, location.longitude
#     except Exception as e:
#         print(f"Error geocoding '{address}': {e}")
#     time.sleep(1)  # Increase delay to respect rate limits
#     return address, None, None

# -------------------- Data Loading Function --------------------

def load_physician_compare_data():
    LOCAL_CSV_PATH = os.path.join(os.getcwd(), "Physician_Compare_National_Download.csv")
    df = pd.read_csv(LOCAL_CSV_PATH, dtype=str)
    
    # Rename columns for consistency
    df = df.rename(columns={
        "NPI": "npi",
        "Ind_PAC_ID": "pac_id",
        "Ind_enrl_ID": "enrollment_id",
        "Provider Last Name": "last_name",
        "Provider First Name": "first_name",
        "Provider Middle Name": "middle_name",
        "suff": "suffix",
        "gndr": "gender",
        "Cred": "credential",
        "Med_sch": "med_school",
        "Grd_yr": "grad_year",
        "Pri_spec": "pri_spec",
        "Sec_spec_1": "sec_spec_1",
        "Sec_spec_2": "sec_spec_2",
        "Sec_spec_3": "sec_spec_3",
        "Sec_spec_4": "sec_spec_4",
        "Sec_spec_all": "sec_spec_all",
        "Org_nm": "organization_name",
        "Org_PAC_ID": "group_pac_id",
        "num_org_mem": "number_of_group_members",
        "adr_ln_1": "address_line_1",
        "adr_ln_2": "address_line_2",
        "ln_2_sprs": "address_line_2_suppression",
        "cty": "city",
        "st": "state",
        "ZIP Code": "zip_code",
        "Telephone Number": "phone_number"
    })
    
    # Strip whitespace from all string values
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Normalize phone numbers
    if "phone_number" in df.columns:
        df["phone_number"] = df["phone_number"].apply(normalize_phone)
    
    # Generate a full address string for geocoding
    df["full_address"] = df.apply(lambda row: format_address(
        row.get("address_line_1"),
        row.get("address_line_2"),
        row.get("city"),
        row.get("state"),
        row.get("zip_code"),
        row.get("address_line_2_suppression")
    ), axis=1)
    
    # The following geocoding steps are commented out.
    # They would normally:
    # 1. Determine unique addresses to geocode.
    # 2. Load a cache of previously geocoded addresses.
    # 3. Parallelize geocoding for new addresses.
    # 4. Map geocoded coordinates back to the DataFrame.
    
    # Instead, we set latitude and longitude to None to bypass geocoding:
    df["latitude"] = None  # Alternatively, leave the caching/geocoding logic here if desired.
    df["longitude"] = None
    
    # Optionally, you could drop the 'full_address' column if it's not needed:
    df.drop(columns=["full_address"], inplace=True)
    
    # -------------------- (Optional) Merge with Additional Data --------------------
    # Placeholder for NPPES data loading
    npi_list = df["npi"].unique().tolist()
    nppes_df = load_nppes_data(npi_list)
    if not nppes_df.empty:
        nppes_df = nppes_df.rename(columns={col: col.lower() for col in nppes_df.columns})
        if "npi" not in nppes_df.columns and "NPI" in nppes_df.columns:
            nppes_df = nppes_df.rename(columns={"NPI": "npi"})
        overlap_cols = set(nppes_df.columns).intersection(set(df.columns)) - {"npi"}
        if overlap_cols:
            nppes_df = nppes_df.drop(columns=list(overlap_cols))
        df = df.merge(nppes_df, on="npi", how="left")
    
    # Placeholder for Plan-Net data loading
    plan_net_df = load_plan_net_data(npi_list)
    if not plan_net_df.empty:
        plan_net_df = plan_net_df.rename(columns={col: col.lower() for col in plan_net_df.columns})
        if "npi" not in plan_net_df.columns and "NPI" in plan_net_df.columns:
            plan_net_df = plan_net_df.rename(columns={"NPI": "npi"})
        overlap_cols = set(plan_net_df.columns).intersection(set(df.columns)) - {"npi"}
        if overlap_cols:
            plan_net_df = plan_net_df.drop(columns=list(overlap_cols))
        df = df.merge(plan_net_df, on="npi", how="left")
    
    return df

# Placeholder functions for additional data (NPPES and Plan-Net)
def load_nppes_data(npi_list=None):
    """Placeholder: return empty DataFrame for NPPES."""
    return pd.DataFrame()

def load_plan_net_data(npi_list=None):
    """Placeholder: return empty DataFrame for Plan-Net."""
    return pd.DataFrame()

# -------------------- Main Script --------------------
def main():
    print("Start running data_loader.py ...")
    pc_df = load_physician_compare_data()
    print("First 5 rows of merged data:")
    print(pc_df.head())
    
    # Save the processed DataFrame to SQLite
    LOCAL_DB_PATH = os.path.join(os.getcwd(), "providers.sqlite")
    conn = sqlite3.connect(LOCAL_DB_PATH)
    pc_df.to_sql(name="providers", con=conn, if_exists="replace", index=False)
    conn.close()
    print(f"Data successfully saved to {LOCAL_DB_PATH}")

if __name__ == "__main__":
    main()
