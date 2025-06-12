import os
import re
import json
import streamlit as st
from google.cloud import vision
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ CONFIG ------------------
# Use a single service account JSON for both Vision and Sheets APIs. The file
# may be provided directly in the credentials folder or via `st.secrets` under
# the `gcp_service_account` table when running on Streamlit Cloud.
SERVICE_ACCOUNT_PATH = 'credentials/service-account.json'

if 'gcp_service_account' in st.secrets:
    os.makedirs('credentials', exist_ok=True)
    # st.secrets can return objects that aren't plain dictionaries. Convert
    # them to a regular dict before dumping so ``json.dump`` doesn't fail.
    creds = st.secrets['gcp_service_account']
    if not isinstance(creds, dict):
        try:
            creds = dict(creds)
        except Exception:
            creds = json.loads(str(creds))
    with open(SERVICE_ACCOUNT_PATH, 'w') as f:
        json.dump(creds, f)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_PATH
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDS = ServiceAccountCredentials.from_json_keyfile_name(
    SERVICE_ACCOUNT_PATH, SCOPES)
GSPREAD_CLIENT = gspread.authorize(CREDS)
SPREADSHEET_ID = st.secrets['sheet_id']
SHEET_NAME = 'Inventory'
PRODUCT_COL = 'ProductCode'
LOCATION_COL = 'Location'

# ------------------ FUNCTIONS ------------------
def extract_pairs_from_image(image_bytes):
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    text = response.full_text_annotation.text
    pattern = re.compile(r"([A-Z0-9]+)\s+([A-Z0-9-]+)")
    return [(c.strip(), l.strip()) for c, l in pattern.findall(text)]


def load_sheet():
    sheet = GSPREAD_CLIENT.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    df = pd.DataFrame(sheet.get_all_records())
    df.set_index(PRODUCT_COL, inplace=True, drop=False)
    return sheet, df


def apply_updates(sheet, df, updates):
    col_idx = df.columns.get_loc(LOCATION_COL) + 1
    for code, new_loc in updates:
        if code in df.index:
            row = df.index.get_loc(code) + 2
            sheet.update_cell(row, col_idx, new_loc)
        else:
            st.warning(f"Code not found: {code}")

# ------------------ UI ------------------
st.title("\U0001F4E6 Pallet Location Uploader")
uploaded = st.file_uploader("Upload scanned sheet (PDF or image)", ['png','jpg','jpeg','pdf'])
if uploaded:
    data = uploaded.read()
    st.info("Processing...")
    pairs = extract_pairs_from_image(data)
    if not pairs:
        st.error("No entries found.")
    else:
        df = pd.DataFrame(pairs, columns=[PRODUCT_COL, LOCATION_COL])
        st.dataframe(df)
        if st.button("Apply updates"):
            sheet, master = load_sheet()
            apply_updates(sheet, master, pairs)
            st.success("Inventory updated!")
            st.balloons()
