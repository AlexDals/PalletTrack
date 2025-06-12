import os
import re
import difflib
import json
import pandas as pd
import gspread
from google.cloud import vision
from oauth2client.service_account import ServiceAccountCredentials

SERVICE_ACCOUNT_PATH = 'credentials/service-account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Google Sheet constants
SPREADSHEET_ID = os.environ.get('SHEET_ID')
SHEET_NAME = 'Inventory'
PRODUCT_COL = 'ProductCode'
LOCATION_COL = 'Location'
QTY_COL = 'Qty'


def load_credentials():
    if not os.path.exists(SERVICE_ACCOUNT_PATH) and 'gcp_service_account' in os.environ:
        os.makedirs('credentials', exist_ok=True)
        with open(SERVICE_ACCOUNT_PATH, 'w') as fh:
            json.dump(json.loads(os.environ['gcp_service_account']), fh)
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_PATH, SCOPES)
    return gspread.authorize(creds)


def read_pdf_text(path):
    client = vision.ImageAnnotatorClient()
    with open(path, 'rb') as fh:
        content = fh.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    return response.full_text_annotation.text


def parse_tables(text):
    de_rows, a_rows = [], []
    section = None
    for line in text.splitlines():
        l = line.strip()
        if 'DE' in l and 'Produit' in l:
            section = 'DE'
            continue
        if l.startswith('A') and 'Produit' in l:
            section = 'A'
            continue
        tokens = re.findall(r'[A-Z0-9-]+', l)
        if section == 'DE' and len(tokens) >= 2:
            de_rows.append({'product': tokens[0], 'location': tokens[1]})
        if section == 'A' and len(tokens) >= 3:
            a_rows.append({'product': tokens[1], 'location': tokens[0], 'qty': tokens[2]})
    return de_rows, a_rows


def approximate_match(prod, candidates):
    best, score = None, 0
    for row in candidates:
        s = difflib.SequenceMatcher(None, prod, row['product']).ratio()
        if s > score:
            best, score = row, s
    if score > 0.6:
        return best
    return None


def build_updates(de_rows, a_rows):
    updates = []
    for row in de_rows:
        match = approximate_match(row['product'], a_rows)
        if match:
            updates.append((row['product'], match['location'], match['qty']))
    return updates


def update_sheet(client, updates):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    df = pd.DataFrame(sheet.get_all_records())
    df.set_index(PRODUCT_COL, inplace=True, drop=False)
    loc_col = df.columns.get_loc(LOCATION_COL) + 1
    qty_col = df.columns.get_loc(QTY_COL) + 1
    for prod, new_loc, qty in updates:
        if prod in df.index:
            row = df.index.get_loc(prod) + 2
            sheet.update_cell(row, loc_col, new_loc)
            sheet.update_cell(row, qty_col, qty)
            cell = gspread.utils.rowcol_to_a1(row, loc_col)
            try:
                sheet.update_note(cell, 'Made by AI')
            except Exception:
                pass
        else:
            print(f'SKIP: {prod} not found in sheet')


def main():
    if not SPREADSHEET_ID:
        raise SystemExit('Set SHEET_ID environment variable')
    client = load_credentials()
    text = read_pdf_text(os.path.join(os.path.dirname(__file__), 'Xerox Scan.pdf'))
    de_rows, a_rows = parse_tables(text)
    updates = build_updates(de_rows, a_rows)
    if not updates:
        print('No updates found')
        return
    update_sheet(client, updates)
    print(f'Updated {len(updates)} rows.')


if __name__ == '__main__':
    main()
