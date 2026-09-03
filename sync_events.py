import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1EJLyAMCo_A_WXSO1LpX1MGZBTx8JdjbHColuTTJVUVA"
CREDENTIALS_FILE = "Credentials.json"
HEADERS = ["id", "name", "sport", "status", "event_start", "event_end", "sale_start", "sale_time", "sale_end", "description", "ticket_url", "notes", "spotlight", "spotlight_description", "ticket_status", "ticket_scarcity", "ticket_availability_notes"]

def get_spreadsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

def sync():
    with open("events_db.json") as f:
        events = json.load(f)

    spreadsheet = get_spreadsheet()

    try:
        sheet = spreadsheet.worksheet("Events")
        sheet.clear()
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="Events", rows=100, cols=20)

    rows = [HEADERS]
    for e in events:
        rows.append([e.get(h, "") for h in HEADERS])

    sheet.update(rows, "A1")
    print(f"Synced {len(events)} events to Google Sheets.")

if __name__ == "__main__":
    sync()
