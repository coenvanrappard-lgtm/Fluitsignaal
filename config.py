import json
import os

from google.oauth2.service_account import Credentials

SMTP_USER = "Jouwfluitsignaal@gmail.com"
SPREADSHEET_ID = "1EJLyAMCo_A_WXSO1LpX1MGZBTx8JdjbHColuTTJVUVA"
DASHBOARD_URL = "https://fluitsignaal.com/dashboard.html"
TWILIO_FROM = "+19047562903"


SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")


def google_credentials(scopes):
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        return Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
    local_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    return Credentials.from_service_account_file(local_file, scopes=scopes)
