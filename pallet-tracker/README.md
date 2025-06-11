# Pallet Location Uploader

A Streamlit app that extracts product codes and locations from scanned documents using Google Cloud Vision and updates a Google Sheets inventory.

## Setup
1. Clone the repo.
2. Place your service-account JSON files in `credentials/`.
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
