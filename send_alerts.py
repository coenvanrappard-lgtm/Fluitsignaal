import json
import smtplib
import sys
import gspread
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
from twilio.rest import Client as TwilioClient
from urllib.parse import quote

import config
from config import SMTP_USER, SMTP_PASSWORD, SPREADSHEET_ID, TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, DASHBOARD_URL

def load_events():
    with open("events_db.json") as f:
        return json.load(f)

def is_trial_active(user):
    # Payments not yet enabled — all users have full access
    return True

def load_users():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = config.google_credentials(scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Users")
    rows = sheet.get_all_records()
    for row in rows:
        row["events"] = row["events"].split("|") if row.get("events") else []
        row["reminders"] = row["reminders"].split("|") if row.get("reminders") else ["weekly", "day_before"]
    return rows

def send_email(to_email, subject, body):
    manage_url = f"{DASHBOARD_URL}?email={quote(to_email)}"
    full_body = f"{body}\n\n—\nManage your alerts: {manage_url}"
    msg = MIMEText(full_body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
    print(f"Email sent to {to_email}: {subject}")

def send_sms(to_phone, body):
    client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(to=to_phone, from_=TWILIO_FROM, body=body)
    print(f"SMS sent to {to_phone}")

def channels_for(user, reminder_type):
    """Returns set of channels ('email', 'sms') enabled for this reminder type.
    Supports both new format (day_before_email) and old format (day_before + notifications field)."""
    reminders = user.get("reminders", [])
    channels = set()
    if any("_email" in r or "_sms" in r for r in reminders):
        if f"{reminder_type}_email" in reminders:
            channels.add("email")
        if f"{reminder_type}_sms" in reminders:
            channels.add("sms")
    else:
        if reminder_type in reminders:
            notif = user.get("notifications", "email").strip().lower() or "email"
            if notif in ("email", "both"):
                channels.add("email")
            if notif in ("sms", "both"):
                channels.add("sms")
    return channels

def notify_channels(user, channels, subject, email_body, sms_body):
    if "email" in channels and user.get("email"):
        send_email(user["email"], subject, email_body)
    if "sms" in channels and user.get("phone"):
        send_sms(user["phone"], sms_body)

def check_day_before():
    """Run daily at 9am — sends day-before reminders."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    users = load_users()
    events = {e["id"]: e for e in load_events()}

    for user in users:
        if not is_trial_active(user):
            continue
        ch = channels_for(user, "day_before")
        if not ch:
            continue
        name = user["name"]
        for event_id in user["events"]:
            event = events.get(event_id)
            if not event or not event.get("sale_start"):
                continue
            sale_date = datetime.strptime(event["sale_start"], "%Y-%m-%d").date()
            sale_time = event.get("sale_time", "")
            time_str = f" at {sale_time}" if sale_time else ""

            if sale_date == tomorrow:
                notify_channels(user, ch,
                    f"Tomorrow: {event['name']} tickets on sale",
                    f"Hi {name},\n\nReminder: {event['name']} tickets go on sale tomorrow{time_str}.\n\n{event.get('description', '')}\n\nBuy here: {event.get('ticket_url', '')}\n\nGood luck!",
                    f"Fluitsignaal: {event['name']} tickets go on sale TOMORROW{time_str}. {event.get('ticket_url', '')}"
                )

            if event.get("status") == "action_required" and event.get("notes") and sale_date == tomorrow:
                notify_channels(user, ch,
                    f"Action required: {event['name']}",
                    f"Hi {name},\n\nAction needed for {event['name']} tomorrow{time_str}!\n\n{event['notes']}\n\nGo here now: {event.get('ticket_url', '')}\n\nDon't wait!",
                    f"Fluitsignaal: Action required for {event['name']} tomorrow! {event['notes']} {event.get('ticket_url', '')}"
                )

def check_hour_before():
    """Run every hour — sends 1-hour-before reminders for events with a known sale_time."""
    now = datetime.now()
    today = now.date()
    target_hour = (now + timedelta(hours=1)).strftime("%H:%M")
    users = load_users()
    events = {e["id"]: e for e in load_events()}

    for user in users:
        if not is_trial_active(user):
            continue
        ch = channels_for(user, "hour_before")
        if not ch:
            continue
        name = user["name"]
        for event_id in user["events"]:
            event = events.get(event_id)
            if not event or not event.get("sale_start") or not event.get("sale_time"):
                continue
            sale_date = datetime.strptime(event["sale_start"], "%Y-%m-%d").date()
            if sale_date != today:
                continue
            if event["sale_time"].strip()[:5] == target_hour:
                notify_channels(user, ch,
                    f"1 hour left: {event['name']} tickets on sale at {event['sale_time']}",
                    f"Hi {name},\n\n{event['name']} tickets go on sale in 1 hour at {event['sale_time']}.\n\n{event.get('description', '')}\n\nGet ready: {event.get('ticket_url', '')}\n\nGood luck!",
                    f"Fluitsignaal: {event['name']} tickets go on sale in 1 HOUR ({event['sale_time']}). Get ready: {event.get('ticket_url', '')}"
                )

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "day_before"
    if mode == "hour_before":
        check_hour_before()
    else:
        check_day_before()
