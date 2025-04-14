import os
import sqlite3
import pandas as pd
import requests


# Paths and URLs
CMS_CSV_PATH = os.path.join(os.getcwd(), "Physician_Compare_National_Download.csv")  # Path to CMS Physician Compare CSV
NUCC_TAXONOMY_CSV_URL = "https://www.nucc.org/images/stories/CSV/nucc_taxonomy_250.csv"
LOCAL_TAXONOMY_PATH = os.path.join(os.getcwd(), "nucc_taxonomy_250.csv")
DB_PATH = os.path.join(os.getcwd(), "providers.db")

# Download the NUCC taxonomy CSV if not already present
if not os.path.exists(LOCAL_TAXONOMY_PATH):
    try:
        print("Downloading NUCC taxonomy data...")
        response = requests.get(NUCC_TAXONOMY_CSV_URL)
        response.raise_for_status()
        with open(LOCAL_TAXONOMY_PATH, "wb") as f:
            f.write(response.content)
        print("Downloaded NUCC taxonomy CSV to", LOCAL_TAXONOMY_PATH)
    except Exception as e:
        print("Failed to download NUCC taxonomy CSV. Please download it manually.", e)
        raise

# Load the NUCC taxonomy CSV to build a normalization map for specialty names
taxonomy_df = pd.read_csv(LOCAL_TAXONOMY_PATH, dtype=str)
taxonomy_df.fillna("", inplace=True)  # Replace NaN with empty string for easier handling
# Build a set of official specialty names (classification and specialization) from the taxonomy
official_specialties = set()
for _, row in taxonomy_df.iterrows():
    classification = row.get("Classification", "").strip()
    specialization = row.get("Specialization", "").strip()
    if specialization:  # If there is a specialization, include it
        official_specialties.add(specialization)
    if classification:  # Include classification as well (acts as a specialty when no specialization)
        official_specialties.add(classification)
# Create a mapping from uppercase specialty name to official casing
specialty_name_map = {name.upper(): name for name in official_specialties}

# Load the CMS Physician Compare data
if not os.path.exists(CMS_CSV_PATH):
    raise FileNotFoundError(f"CMS data file not found at {CMS_CSV_PATH}. Please update CMS_CSV_PATH.")
print("Loading CMS Physician Compare data...")
# Read CSV with all columns as strings (to preserve IDs, ZIP codes, etc.)
providers_df = pd.read_csv(CMS_CSV_PATH, dtype=str)

# Rename columns from the revised dataset to the original short names (for consistency)
rename_map = {
    "Provider Last Name": "lst_nm",
    "Provider First Name": "frst_nm",
    "Provider Middle Name": "mid_nm",
    "Suffix": "suff",
    "Gender": "gndr",
    "Credential": "cred",
    "Medical school": "med_sch",
    "Medical School": "med_sch",            # Handle possible variations
    "Graduation year": "grd_yr",
    "Graduation Year": "grd_yr",
    "Primary specialty": "pri_spec",
    "Primary Specialty": "pri_spec",
    "Secondary specialty 1": "sec_spec_1",
    "Secondary Specialty 1": "sec_spec_1",
    "Secondary specialty 2": "sec_spec_2",
    "Secondary Specialty 2": "sec_spec_2",
    "Secondary specialty 3": "sec_spec_3",
    "Secondary Specialty 3": "sec_spec_3",
    "Secondary specialty 4": "sec_spec_4",
    "Secondary Specialty 4": "sec_spec_4",
    "All secondary specialties": "sec_spec_all",
    "All Secondary Specialties": "sec_spec_all",
    "Telehealth": "telehlth",
    "Facility Name": "org_nm",
    "Organization legal name": "org_nm",    # In case older name is used
    "Group PAC ID": "org_pac_id",
    "Individual PAC ID": "ind_pac_id",
    "PAC ID": "ind_pac_id",
    "Clinician Enrollment ID": "ind_enrl_id",
    "Number of Group Members": "num_org_mem",
    "Number of group members": "num_org_mem",
    "Line 1 Street Address": "adr_ln_1",
    "Address Line 1": "adr_ln_1",
    "Line 2 Street Address": "adr_ln_2",
    "Address Line 2": "adr_ln_2",
    "City": "cty",
    "City Town": "cty",
    "City/Town": "cty",
    "State": "st",
    "ZIP": "zip",
    "ZIP Code": "zip",
    "Phone Number": "phn_numbr",
    "Telephone Number": "phn_numbr",
    "Clinician accepts Medicare Assignment": "assgn",
    "Clinician accepts Medicare assignment": "assgn",
    "Group accepts Medicare Assignment": "grp_assgn",
    "Group accepts Medicare assignment": "grp_assgn",
    "Address ID": "adrs_id"
}
# Apply renaming for any columns that match
for col, new_col in rename_map.items():
    if col in providers_df.columns:
        providers_df.rename(columns={col: new_col}, inplace=True)

# Strip whitespace from all string values to ensure clean data
providers_df = providers_df.map(lambda x: x.strip() if isinstance(x, str) else x)

# Normalize specialty names (primary and secondary) using the taxonomy mapping
spec_cols = ["pri_spec", "sec_spec_1", "sec_spec_2", "sec_spec_3", "sec_spec_4"]
for col in spec_cols:
    if col in providers_df.columns:
        providers_df[col] = providers_df[col].apply(
            lambda val: specialty_name_map.get(val.strip().upper(), val) if pd.notna(val) else val
        )

# Recalculate the combined secondary specialties column to reflect normalized names
if all(col in providers_df.columns for col in ["sec_spec_1", "sec_spec_2", "sec_spec_3", "sec_spec_4"]):
    combined_list = providers_df[["sec_spec_1", "sec_spec_2", "sec_spec_3", "sec_spec_4"]].fillna("").values.tolist()
    sec_all = []
    for specs in combined_list:
        # Filter out empty strings and join multiple specialties with comma + space
        specs_clean = [s for s in specs if s and str(s).strip() != ""]
        if specs_clean:
            sec_all.append(", ".join(specs_clean))
        else:
            sec_all.append("")
    providers_df["sec_spec_all"] = sec_all

# Replace any remaining NaN values with None (to store as NULL in database)
providers_df = providers_df.where(pd.notna(providers_df), None)

# Create SQLite database and table, then insert data
print("Creating SQLite database and inserting data...")
conn = sqlite3.connect(DB_PATH)
# Use pandas to_sql to create and populate the providers table
providers_df.to_sql("providers", conn, if_exists="replace", index=False)

# Create indexes on searchable fields for performance
cur = conn.cursor()
try:
    cur.execute("CREATE INDEX idx_prov_last_name ON providers(lst_nm)")
    cur.execute("CREATE INDEX idx_prov_first_name ON providers(frst_nm)")
    if "pri_spec" in providers_df.columns:
        cur.execute("CREATE INDEX idx_prov_pri_spec ON providers(pri_spec)")
    if "sec_spec_1" in providers_df.columns:
        cur.execute("CREATE INDEX idx_prov_sec_spec1 ON providers(sec_spec_1)")
    if "sec_spec_2" in providers_df.columns:
        cur.execute("CREATE INDEX idx_prov_sec_spec2 ON providers(sec_spec_2)")
    if "sec_spec_3" in providers_df.columns:
        cur.execute("CREATE INDEX idx_prov_sec_spec3 ON providers(sec_spec_3)")
    if "sec_spec_4" in providers_df.columns:
        cur.execute("CREATE INDEX idx_prov_sec_spec4 ON providers(sec_spec_4)")
    cur.execute("CREATE INDEX idx_prov_state ON providers(st)")
    cur.execute("CREATE INDEX idx_prov_zip ON providers(zip)")
    conn.commit()
finally:
    cur.close()
    conn.close()

print(f"Database created at {DB_PATH} with {len(providers_df)} provider records.")
print("Indexes on name, specialties, state, and ZIP code have been created.")
