# Pallet Location Uploader

A Streamlit app that extracts product codes and locations from scanned documents using Google Cloud Vision and updates a Google Sheets inventory.

## Setup
1. Clone the repo.
2. Place your service-account JSON file in `credentials/service-account.json`.
   The same credentials are used for both Vision and Sheets. When deploying
   to Streamlit Cloud, you can instead store the values in `secrets.toml`
   under the `[gcp_service_account]` table.
3. Create `.streamlit/credentials.toml`:
   ```toml
   [general]
   email = "your-email@example.com"
   ```
4. Add your `sheet_id` to `secrets.toml` or Streamlit Cloud secrets.
5. Run locally:
   ```bash
   streamlit run app.py
   ```
6. Or build & run Docker:
   ```bash
   docker build -t pallet-tracker .
   docker run -p 8501:8501 pallet-tracker
   ```
