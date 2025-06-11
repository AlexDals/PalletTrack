import os
import re
import streamlit as st
from google.cloud import vision
import pandas as pd
import gspread
from google.oauth2 import service_account

# ------------------ CONFIG ------------------
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

if 'vision_service_account' in st.secrets:
    vision_creds = service_account.Credentials.from_service_account_info(
        st.secrets['vision_service_account']
    )
else:
    vision_creds = service_account.Credentials.from_service_account_file(
        'credentials/vision-service-account.json'
    )

vision_client = vision.ImageAnnotatorClient(credentials=vision_creds)

if 'sheets_service_account' in st.secrets:
    gspread_client = gspread.service_account_from_dict(
        st.secrets['sheets_service_account'], scopes=SCOPES
    )
else:
    gspread_client = gspread.service_account(
        filename='credentials/sheets-service-account.json', scopes=SCOPES
    )

SPREADSHEET_ID = st.secrets['sheet_id']
SHEET_NAME = 'Inventory'
PRODUCT_COL = 'ProductCode'
LOCATION_COL = 'Location'

# ------------------ FUNCTIONS ------------------
def extract_pairs_from_image(image_bytes):
    image = vision.Image(content=image_bytes)
    response = vision_client.document_text_detection(image=image)
    text = response.full_text_annotation.text
    pattern = re.compile(r"([A-Z0-9]+)\s+([A-Z0-9-]+)")
    return [(c.strip(), l.strip()) for c, l in pattern.findall(text)]


def load_sheet():
    sheet = gspread_client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
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
