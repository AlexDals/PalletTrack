import os
import re
import streamlit as st
from google.cloud import vision
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ CONFIG ------------------
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials/vision-service-account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDS = ServiceAccountCredentials.from_json_keyfile_name(
    'credentials/sheets-service-account.json', SCOPES)
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
