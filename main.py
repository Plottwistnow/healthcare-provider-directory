import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
#from data_loader import geocode_address  # Reuse the existing geocoding function

# --- Data Loading and Caching ---
@st.cache_data
def load_provider_data():
    """Load provider data from the SQLite database and return as DataFrame."""
    conn = sqlite3.connect('providers.db')
    df = pd.read_sql("SELECT * FROM providers", conn)
    conn.close()
    # Rename columns for clarity (if applicable)
    col_renames = {
        'frst_nm': 'first_name',
        'lst_nm': 'last_name',
        'mid_nm': 'middle_name',
        'cty': 'city',
        'st': 'state',
        'zip': 'zip_code',
        'phn_numbr': 'phone',
        'assgn': 'medicare_assignment',
        'Is_Telehealth': 'telehealth'
    }
    df.rename(columns={k: v for k, v in col_renames.items() if k in df.columns}, inplace=True)
    # If the data has separate name fields, create a full name for easy display/search
    if 'first_name' in df.columns and 'last_name' in df.columns:
        df['provider_name'] = df['first_name'].str.strip() + " " + df['last_name'].str.strip()
        df['provider_name'] = df['provider_name'].str.replace(r'\s+', ' ', regex=True)  # clean double spaces
    else:
        # If there's already a combined name field, use it
        df['provider_name'] = df.get('provider_name', df.get('name'))
    return df

# Load data
providers_df = load_provider_data()

# --- Sidebar Filters ---
st.sidebar.header("Filter Providers")
# Full-text search input
search_query = st.sidebar.text_input("Search (Name, City, Specialty)")
# Primary Specialty multiselect (unique values from primary specialty field)
if 'pri_spec' in providers_df.columns:
    all_specialties = sorted(providers_df['pri_spec'].dropna().unique().tolist())
else:
    all_specialties = []
selected_specialties = st.sidebar.multiselect("Primary Specialty", all_specialties)
# State multiselect (two-letter state codes)
if 'state' in providers_df.columns:
    all_states = sorted(providers_df['state'].dropna().unique().tolist())
else:
    all_states = []
selected_states = st.sidebar.multiselect("State", all_states)
# Location (City or ZIP) and Radius
location_input = st.sidebar.text_input("City or ZIP Code")
radius = st.sidebar.slider("Search radius (miles)", min_value=0, max_value=100, value=0)
# Network Adequacy toggle
show_network = st.sidebar.checkbox("Network Adequacy Analysis")

# --- Apply Filters to Data ---
df_filtered = providers_df.copy()

# 1. Full-text search across name, city, and specialties
if search_query:
    query = search_query.strip().lower()
    # Filter rows where any relevant field contains the query substring (case-insensitive)
    df_filtered = df_filtered[
        df_filtered['provider_name'].str.contains(query, case=False, na=False) |
        df_filtered['city'].str.contains(query, case=False, na=False) |
        df_filtered['pri_spec'].str.contains(query, case=False, na=False) |
        df_filtered.get('sec_spec_1', pd.Series(dtype=str)).str.contains(query, case=False, na=False) |
        df_filtered.get('sec_spec_2', pd.Series(dtype=str)).str.contains(query, case=False, na=False) |
        df_filtered.get('sec_spec_3', pd.Series(dtype=str)).str.contains(query, case=False, na=False) |
        df_filtered.get('sec_spec_4', pd.Series(dtype=str)).str.contains(query, case=False, na=False)
    ]

# 2. Primary specialty filter
if selected_specialties:
    df_filtered = df_filtered[df_filtered['pri_spec'].isin(selected_specialties)]

# 3. State filter
if selected_states:
    df_filtered = df_filtered[df_filtered['state'].isin(selected_states)]

# 4. Location + radius filter
center_lat, center_lon = None, None
if location_input:
    # Geocode the input location (could be city/state or ZIP)
    center_lat, center_lon = geocode_address(location_input)
    if center_lat is not None and center_lon is not None and radius is not None and radius > 0:
        # Ensure provider data has latitude/longitude columns for distance calculation
        if 'lat' in df_filtered.columns and 'lon' in df_filtered.columns:
            # Convert to radians for vectorized haversine calculation
            lat_r = np.radians(df_filtered['lat'].astype(float))
            lon_r = np.radians(df_filtered['lon'].astype(float))
            clat_r = np.radians(center_lat)
            clon_r = np.radians(center_lon)
            # Haversine formula for distance in miles
            dlat = lat_r - clat_r
            dlon = lon_r - clon_r
            a = np.sin(dlat/2)**2 + np.cos(clat_r) * np.cos(lat_r) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            distances = 3958.8 * c  # Earth radius ~3958.8 miles
            # Filter providers within the radius
            mask = distances <= radius
            df_filtered = df_filtered[mask].copy()
            df_filtered['distance_miles'] = distances[mask].round(1)  # store distance (rounded) for display
            # Sort by distance (nearest first)
            df_filtered.sort_values('distance_miles', inplace=True)
        else:
            # If no coordinates in data, cannot apply radius filter
            st.warning("Provider coordinates not available for radius filtering.")
            # (If needed, could fall back to filtering by exact city/ZIP match as a crude approach)
# --- Display Results in Main Section ---

# Header for results
st.title("Provider Directory")
num_results = len(df_filtered)
st.markdown(f"**Found {num_results} providers** matching your criteria.")

# Map of providers (if any and if coordinates available)
if num_results > 0:
    if 'lat' in df_filtered.columns and 'lon' in df_filtered.columns:
        # Drop rows without coordinates to plot
        map_data = df_filtered[['lat', 'lon']].dropna()
        if not map_data.empty:
            st.map(map_data)  # Plot all provider locations on a map&#8203;:contentReference[oaicite:3]{index=3}
    else:
        st.info("Map view not available (missing provider coordinates in data).")


# --- Provider table with pagination ---
if num_results > 0:
    # Build a list of dictionary records from the filtered data (all rows)
    table_records = []
    for idx, row in df_filtered.iterrows():
        # Build Provider Name (use 'provider_name' field; append credential if available)
        name_line = row.get('provider_name', '')
        if row.get('Cred') and pd.notna(row.get('Cred')):
            name_line += ", " + str(row['Cred'])
        
        # Build Specialty string: combine primary specialty with secondary specialties
        specialties = ""
        if row.get('pri_spec'):
            specialties = str(row['pri_spec'])
        sec_list = []
        for col in ['sec_spec_1', 'sec_spec_2', 'sec_spec_3', 'sec_spec_4']:
            val = row.get(col)
            if val and pd.notna(val) and str(val).strip():
                sec_list.append(str(val))
        if sec_list:
            specialties += "; " + "; ".join(sec_list)
        
        # Build Address string: combine address line 1, address line 2, and City/State/ZIP
        address_parts = []
        if row.get('adr_ln_1'):
            address_parts.append(str(row['adr_ln_1']).strip())
        if row.get('adr_ln_2') and str(row['adr_ln_2']).strip():
            address_parts.append(str(row['adr_ln_2']).strip())
        city_state_zip = []
        if row.get('city'):
            city_state_zip.append(str(row['city']).strip())
        if row.get('state'):
            city_state_zip.append(str(row['state']).strip())
        if row.get('zip_code'):
            city_state_zip.append(str(row['zip_code']).strip())
        if city_state_zip:
            address_parts.append(", ".join(city_state_zip))
        address = "; ".join(address_parts)
        
        # Phone number
        phone = str(row.get('phone')).strip() if row.get('phone') else ""
        
        # Telehealth availability
        tele = row.get('telehealth')
        if tele and pd.notna(tele):
            tele = str(tele).strip().upper()
            tele_text = "Yes" if tele in ["Y", "TRUE", "1"] else "No"
        else:
            tele_text = "No"
        
        # Medicare assignment acceptance
        assign_val = row.get('medicare_assignment')
        if assign_val and pd.notna(assign_val):
            assign_val = str(assign_val).strip().upper()
            if assign_val == 'Y':
                assign_text = "Yes"
            elif assign_val == 'M':
                assign_text = "Partial (May Accept)"
            else:
                assign_text = assign_val
        else:
            assign_text = ""
        
        # Distance (if calculated)
        distance = row.get('distance_miles', "")
        
        # Append all collected fields to the records list
        table_records.append({
            "Provider Name": name_line,
            "Specialty": specialties,
            "Address": address,
            "Phone": phone,
            "Telehealth": tele_text,
            "Accepts Medicare": assign_text,
            "Distance (miles)": distance
        })

    # Convert records to DataFrame
    table_df = pd.DataFrame(table_records)
    
    # --- Pagination ---
    page_size = 20
    total_rows = len(table_df)
    total_pages = (total_rows - 1) // page_size + 1
    
    # Create a number input for the page number if more than one page exists
    if total_pages > 1:
        page_number = st.number_input("Page", min_value=1, max_value=total_pages, step=1, value=1)
    else:
        page_number = 1
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size

    # Display the paginated table
    st.table(table_df.iloc[start_idx:end_idx])




# --- Network Adequacy Analysis ---
if show_network:
    st.header("Network Adequacy Analysis")
    # Hardcoded population data (by state for simplicity)
    population = {
        'AL': 4903185, 'AK': 731545, 'AZ': 7278717, 'AR': 3017804, 'CA': 39512223,
        'CO': 5758736, 'CT': 3565287, 'DE': 973764, 'DC': 705749, 'FL': 21477737,
        'GA': 10617423, 'HI': 1415872, 'ID': 1787065, 'IL': 12671821, 'IN': 6732219,
        'IA': 3155070, 'KS': 2913314, 'KY': 4467673, 'LA': 4648794, 'ME': 1344212,
        'MD': 6045680, 'MA': 6892503, 'MI': 9986857, 'MN': 5639632, 'MS': 2976149,
        'MO': 6137428, 'MT': 1068778, 'NE': 1934408, 'NV': 3080156, 'NH': 1359711,
        'NJ': 8882190, 'NM': 2096829, 'NY': 19453561, 'NC': 10488084, 'ND': 762062,
        'OH': 11689100, 'OK': 3956971, 'OR': 4217737, 'PA': 12801989, 'RI': 1059361,
        'SC': 5148714, 'SD': 884659, 'TN': 6829174, 'TX': 28995881, 'UT': 3205958,
        'VT': 623989, 'VA': 8535519, 'WA': 7614893, 'WV': 1792147, 'WI': 5822434,
        'WY': 578759
    }
    # Determine relevant population (for selected states or overall)
    if selected_states:
        # Use selected states to determine population base
        pop_total = sum(population.get(st, 0) for st in selected_states)
        region_desc = "selected states"
    elif location_input:
        # If no state filter, use state(s) of providers in results (approximate region)
        states_in_results = df_filtered['state'].unique()
        pop_total = sum(population.get(st, 0) for st in states_in_results)
        region_desc = f"region around **{location_input}**"
    else:
        # Default: use all states (national total) if no specific region filter
        pop_total = sum(population.values())
        region_desc = "the entire United States"
    provider_count = len(df_filtered)
    st.write(f"**Region:** {region_desc}")
    st.write(f"**Total population (approx):** {pop_total:,}")
    st.write(f"**Total providers (filtered):** {provider_count}")
    if pop_total > 0:
        providers_per_100k = (provider_count / pop_total) * 100000
        st.write(f"**Providers per 100,000 population:** {providers_per_100k:.1f}")
        # Example benchmark: ~50 per 100k is one provider per 2,000 people&#8203;:contentReference[oaicite:4]{index=4}
        benchmark = 50.0
        if providers_per_100k >= benchmark:
            st.success(f"Provider density is above the common adequacy benchmark (~{benchmark} per 100k).")
        else:
            st.warning(f"Provider density is below the common adequacy benchmark (~{benchmark} per 100k).")
    else:
        st.write("Population data not available for the selected region.")
