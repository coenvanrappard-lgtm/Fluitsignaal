import smtplib
import json
import gspread
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
from urllib.parse import quote
from twilio.rest import Client as TwilioClient

import config
from config import SMTP_USER, SMTP_PASSWORD, SPREADSHEET_ID, TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, DASHBOARD_URL

def load_events():
    with open("events_db.json") as f:
        return json.load(f)

def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = config.google_credentials(scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet("Users")

def format_date_short(date_str):
    if not date_str:
        return ""
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B")

def gcal_link(name, sale_start):
    if not sale_start:
        return ""
    dt = datetime.strptime(sale_start, "%Y-%m-%d")
    start = dt.strftime("%Y%m%d")
    end = (dt + timedelta(days=1)).strftime("%Y%m%d")
    title = quote(f"Ticket sale opens: {name}")
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={start}/{end}"

def build_digest_sections(user_event_ids):
    today = date.today()
    all_events = load_events()
    events = [e for e in all_events if e["id"] in user_event_ids]

    on_sale, action_required, opening_soon, coming_later, monitoring = [], [], [], [], []

    for e in events:
        if not e.get("sale_start"):
            monitoring.append(e)
            continue
        sale_date = datetime.strptime(e["sale_start"], "%Y-%m-%d").date()
        days_away = (sale_date - today).days
        sale_end = e.get("sale_end")
        days_until_close = (datetime.strptime(sale_end, "%Y-%m-%d").date() - today).days if sale_end else 999

        if e.get("status") == "action_required":
            action_required.append((days_away, e))
        elif e.get("status") == "on_sale" or days_away <= 0:
            on_sale.append((days_away, e))
        elif 0 < days_away <= 14:
            opening_soon.append((days_away, e))
        else:
            coming_later.append((days_away, e))

    for lst in [on_sale, action_required, opening_soon, coming_later]:
        lst.sort(key=lambda x: x[0])

    live_section = ""
    if on_sale:
        cards = ""
        for _, e in on_sale:
            event_start = format_date_short(e.get("event_start", ""))
            event_end = format_date_short(e.get("event_end", ""))
            dates = f"{event_start} – {event_end}" if event_start and event_end else event_start
            btn = f'<a href="{e.get("ticket_url","")}" style="display:inline-block;background:#166534;color:#fff;padding:9px 20px;border-radius:5px;font-size:13px;font-weight:500;text-decoration:none;margin-top:10px;">Tickets are live →</a>' if e.get("ticket_url") else ""
            cards += f'<tr><td style="padding:16px 0;border-bottom:0.5px solid #ebebeb;"><div style="font-size:15px;font-weight:600;">{e["name"]}</div><div style="font-size:12px;color:#888;margin-top:3px;">{dates}</div>{btn}</td></tr>'
        live_section = f'<tr><td style="padding:1.5rem 0 0.25rem;"><div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#166534;">Live now</div></td></tr>{cards}'

    attention_section = ""
    if action_required:
        cards = ""
        for _, e in action_required:
            notes = e.get("notes", "")
            detail = f'<div style="font-size:13px;color:#854d0e;margin-top:6px;padding:8px 12px;background:#fef9c3;border-left:3px solid #d97706;">{notes}</div>' if notes else '<div style="font-size:13px;color:#991b1b;margin-top:6px;padding:8px 12px;background:#fee2e2;border-left:3px solid #991b1b;">Action required — check the ticket page for details.</div>'
            sale_date_line = f'<div style="font-size:12px;color:#888;margin-top:3px;">Sale opens {format_date_short(e.get("sale_start",""))}</div>' if e.get("sale_start") else ""
            btn = f'<a href="{e.get("ticket_url","")}" style="display:inline-block;background:#1a1a1a;color:#fff;padding:8px 18px;border-radius:5px;font-size:13px;font-weight:500;text-decoration:none;margin-top:10px;">Take action →</a>' if e.get("ticket_url") else ""
            cards += f'<tr><td style="padding:16px 0;border-bottom:0.5px solid #ebebeb;"><div style="font-size:15px;font-weight:600;">{e["name"]}</div>{sale_date_line}{detail}{btn}</td></tr>'
        attention_section = f'<tr><td style="padding:1.5rem 0 0.25rem;"><div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#991b1b;">Needs attention</div></td></tr>{cards}'

    coming_section = ""
    all_coming = opening_soon + coming_later
    if all_coming:
        rows = ""
        for days_away, e in all_coming:
            cal = gcal_link(e["name"], e.get("sale_start", ""))
            cal_link_html = f'&nbsp;<a href="{cal}" style="font-size:11px;color:#aaa;text-decoration:none;">+ calendar</a>' if cal else ""
            rows += f'<tr><td style="padding:8px 0;border-bottom:0.5px solid #f5f5f5;font-size:13px;color:#1a1a1a;">{e["name"]}</td><td style="padding:8px 0;border-bottom:0.5px solid #f5f5f5;font-size:13px;color:#666;text-align:right;white-space:nowrap;">sale opens {format_date_short(e.get("sale_start",""))} {cal_link_html}</td></tr>'
        coming_section = f'<tr><td style="padding:1.5rem 0 0.5rem;"><div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#1e40af;margin-bottom:10px;">Coming up</div><table width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>'

    monitoring_section = ""
    if monitoring:
        rows = ""
        for e in monitoring:
            rows += f'<tr><td style="padding:8px 0;border-bottom:0.5px solid #f5f5f5;font-size:13px;color:#1a1a1a;">{e["name"]}</td><td style="padding:8px 0;border-bottom:0.5px solid #f5f5f5;font-size:13px;color:#aaa;text-align:right;">Date TBA</td></tr>'
        monitoring_section = f'<tr><td style="padding:1.5rem 0 0.5rem;"><div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#888;margin-bottom:10px;">Monitoring</div><table width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>'

    return live_section, attention_section, coming_section, monitoring_section

def send_welcome(user_name, user_email, user_event_ids, plan):
    today = date.today()
    first_name = user_name.split()[0]
    settings_url = f"{DASHBOARD_URL}?email={quote(user_email)}"

    live_section, attention_section, coming_section, monitoring_section = build_digest_sections(user_event_ids)

    has_content = live_section or attention_section or coming_section or monitoring_section
    digest_block = f"""
    <tr><td style="padding:1.5rem 2rem;border-top:0.5px solid #ebebeb;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#aaa;margin-bottom:0.5rem;">Your first alert overview</div>
      <table width="100%" cellpadding="0" cellspacing="0">
        {live_section}
        {attention_section}
        {coming_section}
        {monitoring_section}
        {'' if has_content else '<tr><td style="padding:2rem 0;text-align:center;color:#bbb;font-size:14px;">Nothing on sale yet - we will alert you as soon as something opens up.</td></tr>'}
      </table>
    </td></tr>
    """ if user_event_ids else ""

    events_list = ""
    if user_event_ids:
        all_events = {e["id"]: e["name"] for e in load_events()}
        names = [all_events.get(eid, eid) for eid in user_event_ids]
        events_list = ", ".join(names)

    html = f"""
    <html><body style="font-family:'Helvetica Neue',Arial,sans-serif;background:#f5f5f3;margin:0;padding:1.5rem;">
    <div style="max-width:540px;margin:0 auto;background:#fff;">

      <div style="padding:1.5rem 2rem;border-bottom:2px solid #1a1a1a;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="font-size:19px;font-weight:700;letter-spacing:-0.3px;">Fluitsignaal</td>
          <td style="text-align:right;font-size:12px;color:#999;">Welcome</td>
        </tr></table>
      </div>

      <div style="padding:1.75rem 2rem;border-bottom:0.5px solid #ebebeb;">
        <div style="font-size:22px;font-weight:700;letter-spacing:-0.3px;margin-bottom:0.75rem;">Hi {first_name}, you're in.</div>
        <div style="font-size:14px;color:#555;line-height:1.7;">
          You're now set up on the <strong>{plan}</strong> plan. We'll email you the moment tickets go on sale for your events — the day before and on the day itself.
        </div>
      </div>

      {'<div style="padding:1.25rem 2rem;border-bottom:0.5px solid #ebebeb;background:#fafafa;"><div style="font-size:12px;font-weight:600;color:#aaa;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Your events</div><div style="font-size:13px;color:#1a1a1a;line-height:1.7;">' + events_list + '</div></div>' if events_list else ''}

      <div style="padding:0 2rem 1.5rem;">
        <table width="100%" cellpadding="0" cellspacing="0">
          {digest_block}
        </table>
      </div>

      <div style="padding:1.25rem 2rem;border-top:0.5px solid #ebebeb;background:#f0fdf4;">
        <div style="font-size:13px;font-weight:600;color:#166534;margin-bottom:4px;">Day-before email alerts are on</div>
        <div style="font-size:13px;color:#374151;line-height:1.6;">You'll get an email the day before each ticket sale opens. You can add SMS alerts or adjust your preferences anytime in your dashboard.</div>
        <a href="{settings_url}" style="display:inline-block;background:#1a1a1a;color:#fff;padding:10px 22px;border-radius:6px;font-size:13px;font-weight:500;text-decoration:none;margin-top:12px;">Manage preferences →</a>
      </div>

      <div style="padding:1.25rem 2rem;border-top:0.5px solid #ebebeb;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="font-size:11px;color:#bbb;line-height:1.6;">You're receiving this because you signed up for Fluitsignaal ticket alerts.</td>
        </tr></table>
      </div>

    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Welcome to Fluitsignaal, {first_name}"
    msg["From"] = SMTP_USER
    msg["To"] = user_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, user_email, msg.as_string())
    print(f"Welcome email sent to {user_email}")

def send_sms_welcome(user_name, user_phone, user_event_ids, plan):
    first_name = user_name.split()[0]
    settings_url = f"{DASHBOARD_URL}?email="
    all_events = {e["id"]: e["name"] for e in load_events()}
    names = [all_events.get(eid, eid) for eid in user_event_ids]
    events_str = ", ".join(names) if names else "no events selected yet"
    body = (
        f"Hi {first_name}, welcome to Fluitsignaal! "
        f"You're on the {plan} plan, tracking: {events_str}. "
        f"We'll text you the moment tickets go on sale. "
        f"Manage your events: {DASHBOARD_URL}"
    )
    client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(to=user_phone, from_=TWILIO_FROM, body=body)
    print(f"Welcome SMS sent to {user_phone}")

def run():
    sheet = get_sheet()
    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    welcome_col = headers.index("welcome_sent") + 1
    signup_date_col = headers.index("signup_date") + 1 if "signup_date" in headers else None

    for i, user in enumerate(rows, start=2):
        if user.get("welcome_sent"):
            continue
        if not user.get("email"):
            continue
        event_ids = user["events"].split("|") if user.get("events") else []
        notif = user.get("notifications", "email").strip().lower() or "email"
        plan = user.get("plan", "free")

        if notif in ("email", "both"):
            send_welcome(user["name"], user["email"], event_ids, plan)
        if notif in ("sms", "both") and user.get("phone"):
            send_sms_welcome(user["name"], user["phone"], event_ids, plan)

        sheet.update_cell(i, welcome_col, "yes")
        if signup_date_col:
            sheet.update_cell(i, signup_date_col, date.today().strftime("%Y-%m-%d"))

if __name__ == "__main__":
    run()
