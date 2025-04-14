# Healthcare Provider Directory

Welcome to the **Healthcare Provider Directory** – where finding a doctor is as easy as ordering your favorite pizza (only healthier)! This web application, built with Streamlit, aggregates data from CMS and health plan APIs to let you search for providers, filter by specialty/location/insurance, view interactive maps, and analyze network adequacy (that’s provider coverage vs. population).

---

## Table of Contents

- [Features](#features)
- [Data Sources](#data-sources)
- [Installation](#installation)
- [Usage Tips](#usage-tips)
- [Deployment](#deployment)
- [Extensibility](#extensibility)
- [References](#references)

---

## Features

- **Search Providers:** Find docs by name or keyword.
- **Filter by Specialty:** E.g., Primary Care, Cardiology, etc.
- **Filter by Location:** Search by state, city, or ZIP code (with a nifty radius search).
- **Filter by Insurance Plan:** Display only providers accepting specific insurance networks (via Plan-Net data).
- **Provider Profiles:** View essential details such as address, phone number, specialty, and insurance participation.
- **Interactive Map:** See provider locations come to life on a map.
- **Network Adequacy Analysis:** Check out provider-to-population ratios and enjoy coverage maps that make sense.

---

## Data Sources

- **CMS Physician Compare (Doctors and Clinicians):** Public dataset of Medicare-participating clinicians.
- **CMS NPPES NPI Registry API:** Real-time provider info for NPI lookups.
- **HL7 Da Vinci PDex Plan-Net APIs:** Insurance provider network data based on FHIR standards.
- **NUCC Provider Taxonomy:** Standard specialty codes for data normalization.
- **US Census Geocoder:** Turns addresses into coordinates for our map magic.

*Pro Tip:* Add actual URLs to these references for quick access if needed!

---

## Installation

### 1. Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/provider-directory-app.git
```

*Not a fan of cloning?* Download the ZIP and extract the files.

### 2. Install Python 3.8+ (Virtual Environment Recommended)

Ensure you have Python 3.8 or higher. Using a virtual environment keeps your dependencies neat and tidy.

### 3. Install Required Packages

Install all necessary packages using pip:

```bash
pip install -r requirements.txt
```

### 4. Download CMS Data

The app uses the CMS Physician Compare dataset, and you have two options:

1. **Automatic Download:**  
   Run `data_loader.py` to automatically fetch the dataset from CMS (data.cms.gov). Just ensure your internet connection is solid – no buffering allowed!

2. **Manual Download:**  
   If the automatic download gives you attitude, download the "National Downloadable File" for Doctors and Clinicians from the CMS Provider Data Catalog and save it as `Physician_Compare_National_Download.csv` in the project directory.

### 5. Configure Plan-Net Endpoints (Optional)

If you have access to an insurer’s Plan-Net FHIR API, edit `data_loader.py` to add your endpoint:

```python
PLAN_NET_ENDPOINTS = {
    "YourPayerName": "https://payer-api.com/fhir/"
}
```

*Heads up:* If the API requires authentication, update `fetch_plans_for_npi` to include your tokens or API keys.

### 6. Run Data Loading

Execute the data loading script:

```bash
python data_loader.py
```

This script will:
- Fetch and/or read the CMS dataset.
- Call the NPPES API for provider details.
- Fetch insurance data from any configured Plan-Net APIs.
- Geocode addresses.
- Save all integrated data into an SQLite database (`providers.db`).

*Note:* This might take a while—use that time to grab a coffee or practice your best "loading" face.

### 7. Launch the Streamlit App

Start the app with the following command:

```bash
streamlit run app.py
```

This will launch the Streamlit development server and open the app in your browser (typically at [http://localhost:8501](http://localhost:8501)). Now you're ready to explore a smarter way to find healthcare providers!

---

## Usage Tips

- **Combining Filters:** Mix and match! For example, search for "John" and select "Cardiology" to see all cardiologists with that name.
- **Geographic Search:** Enter a city or ZIP code (like "10001" for NYC) and adjust the radius slider to find providers in your vicinity.
- **Insurance Filter:** This filter is powered by your Plan-Net data. If it’s empty, consider adding more payers.
- **Performance:** With large datasets, the app might slow down. In that case, consider indexing or optimizing your queries.
- **Network Adequacy:** For a deeper analysis, integrate census population data to compute providers per capita (a heatmap would be a neat bonus).

---

## Deployment

Deploy this app your way:

### Streamlit Cloud

Deploy directly on [Streamlit Cloud](https://share.streamlit.io) for free. Just remember to secure your API keys in the app settings.

### On-Premise or Virtual Machine

Run the app on your own server:

```bash
streamlit run app.py
```

Set up a reverse proxy if needed. It’s like having your own personal hospital—minus the waiting room.

### Docker

For a containerized deployment, create a Dockerfile from this project. Install dependencies and set the entrypoint to Streamlit. Make sure the data loading process is handled appropriately (either in the build process or at container startup).

---

## Extensibility

- **Adding More Data:** Expand the directory with extra fields like provider ratings, patient reviews, or hospital affiliations.
- **UI Improvements:** Level up the UI by using Streamlit’s layout tools (like `st.columns` or `st.container`) for slick, modern card designs.
- **Authentication:** For internal use, consider adding an authentication layer to secure sensitive information.
- **Scaling:** For larger deployments, consider switching to a more robust database (PostgreSQL with PostGIS, or Elasticsearch for full-text search).

---

## References

- **CMS Provider Data Catalog – Doctors and Clinicians Dataset**  
  *Source: data.cms.gov*

- **NPPES NPI Registry API Documentation**  
  *(Great for real-time provider lookup)*

- **HL7 Da Vinci PDex Plan-Net Implementation Guide**  
  *Source: build.fhir.org*

- **NUCC Health Care Provider Taxonomy Code Set**  
  *Source: nucc.org*

- **U.S. Census Geocoder API**  
  *Source: move-coop.github.io*

---