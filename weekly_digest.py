import smtplib
import json
import uuid
import gspread
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
from urllib.parse import quote

import config
from config import SMTP_USER, SMTP_PASSWORD, SPREADSHEET_ID

def load_events():
    with open("events_db.json") as f:
        return json.load(f)

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

def format_date(date_str):
    if not date_str:
        return ""
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")

def format_date_short(date_str):
    if not date_str:
        return ""
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B")

def editorial_blurb(text, limit=120):
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    for punct in (". ", " — ", "; ", ": "):
        idx = cut.rfind(punct)
        if idx > int(limit * 0.55):
            return cut[:idx + (1 if punct == ". " else 0)].rstrip()
    return cut.rstrip(" ,;-") + "..."

def gcal_link(name, sale_start):
    if not sale_start:
        return ""
    dt = datetime.strptime(sale_start, "%Y-%m-%d")
    start = dt.strftime("%Y%m%d")
    end = (dt + timedelta(days=1)).strftime("%Y%m%d")
    title = quote(f"Ticket sale opens: {name}")
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={start}/{end}"

def intro_text(on_sale, closing_soon, action_required, opening_soon):
    parts = []
    live = on_sale + closing_soon
    if live:
        names = " and ".join([e["name"] for _, e in live[:2]])
        if len(live) > 2:
            names += f" and {len(live)-2} more"
        parts.append(f"{names} {'are' if len(live) > 1 else 'is'} live now.")
    if action_required:
        missing_notes = [e for _, e in action_required if not e.get("notes")]
        if missing_notes:
            parts.append(f"{missing_notes[0]['name']} still needs a final detail check.")
        else:
            parts.append(f"{action_required[0][1]['name']} is worth setting up before the sale window opens.")
    if opening_soon:
        next_up = opening_soon[0]
        parts.append(f"Next up: {next_up[1]['name']} in {next_up[0]} days — {format_date_short(next_up[1].get('sale_start', ''))}.")
    if not parts:
        parts.append("A quieter week, but still a few things worth keeping in view.")
    return " ".join(parts)

def build_subject(on_sale, closing_soon, opening_soon, action_required, today):
    active = on_sale + closing_soon
    if active:
        names = " & ".join([e["name"] for _, e in active[:2]])
        return f"Ticket alert: {names} now on sale"
    elif action_required:
        return f"Fluitsignaal: {action_required[0][1]['name']} needs your attention"
    elif opening_soon:
        return f"Fluitsignaal: {opening_soon[0][1]['name']} tickets open in {opening_soon[0][0]} days"
    else:
        return f"Fluitsignaal — {today.strftime('%B %d')}"

def live_card(e, status_type):
    sale_end = e.get("sale_end", "")
    event_start = format_date_short(e.get("event_start", ""))
    event_end = format_date_short(e.get("event_end", ""))
    dates = f"{event_start} – {event_end}" if event_start and event_end else event_start
    description = editorial_blurb(e.get("description", ""), 96)

    if status_type == "closing_soon" and sale_end:
        days_left = (datetime.strptime(sale_end, "%Y-%m-%d").date() - date.today()).days
        eyebrow = '<span style="display:inline-block;font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#991b1b;">Closing soon</span>'
        urgency = f'<div style="font-size:12px;color:#991b1b;margin-top:10px;font-weight:600;">Sale closes in {days_left} days — {format_date_short(sale_end)}</div>'
        btn_text = "Last chance to buy"
        btn_color = "#1a1a1a"
        card_bg = "#ffffff"
        card_border = "#e8d7d7"
        image_border = "#dfd7d2"
    else:
        eyebrow = '<span style="display:inline-block;font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#6b7280;">On sale now</span>'
        urgency = ""
        btn_text = "Tickets are live"
        btn_color = "#166534"
        card_bg = "#ffffff"
        card_border = "#dfe5df"
        image_border = "#d8dcda"

    ticket_url = e.get("ticket_url", "")
    btn = f'<a href="{ticket_url}" style="display:inline-block;background:{btn_color};color:#fff;padding:11px 20px;border-radius:8px;font-size:12px;font-weight:700;text-decoration:none;white-space:nowrap;letter-spacing:-0.01em;min-width:168px;text-align:center;box-sizing:border-box;">{btn_text} →</a>' if ticket_url else ""
    img_url = e.get("image_url", "")
    img_col = f'<td width="186" style="vertical-align:middle;text-align:right;padding:8px 20px 20px 12px;"><img src="{img_url}" width="156" height="118" style="display:block;object-fit:cover;object-position:center top;border-radius:16px;border:1px solid {image_border};box-shadow:0 8px 22px rgba(17,24,39,0.06);background:#f4f4f4;" /></td>' if img_url else ""
    description_html = f'<div style="font-size:14px;color:#58606b;line-height:1.65;margin-top:14px;max-width:360px;">{description}</div>' if description else ""

    return f"""
    <tr>
      <td style="padding:0 0 14px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{card_bg};border:1px solid {card_border};border-radius:22px;"><tr>
          <td colspan="2" style="padding:22px 22px 0;">{eyebrow}</td>
        </tr><tr>
          <td style="vertical-align:top;">
            <div style="padding:10px 0 22px 22px;">
              <div style="font-size:20px;font-weight:700;letter-spacing:-0.03em;color:#1a1a1a;line-height:1.15;">{e['name']}</div>
              <div style="font-size:14px;color:#7a7a7a;margin-top:8px;font-weight:500;">{dates}</div>
              {urgency}
              {description_html}
              <div style="margin-top:18px;">{btn}</div>
            </div>
          </td>
          {img_col}
        </tr></table>
      </td>
    </tr>
    """

def attention_card(e):
    sale_start = e.get("sale_start", "")
    notes = e.get("notes", "")
    img_url = e.get("image_url", "")
    if notes:
        detail = f'<div style="font-size:13px;color:#58606b;padding:12px 14px;background:#fafafa;border:1px solid #ececec;border-radius:10px;line-height:1.65;max-width:360px;">{notes}</div>'
        btn_text = "Get set up"
    else:
        detail = '<div style="font-size:13px;color:#58606b;padding:12px 14px;background:#fafafa;border:1px solid #ececec;border-radius:10px;line-height:1.65;max-width:360px;">A few details still need confirming before reminder emails can go out.</div>'
        btn_text = "View ticket page"

    cal = gcal_link(e["name"], sale_start)
    btn_color = "#166534" if btn_text == "Get set up" else "#1a1a1a"
    btn = f'<a href="{e.get("ticket_url","")}" style="display:inline-block;background:{btn_color};color:#fff;padding:11px 20px;border-radius:8px;font-size:12px;font-weight:700;text-decoration:none;margin-right:8px;letter-spacing:-0.01em;white-space:nowrap;min-width:168px;text-align:center;box-sizing:border-box;">{btn_text} →</a>' if e.get("ticket_url") else ""
    cal_btn = f'<a href="{cal}" style="display:inline-block;background:#f3f4f6;color:#374151;padding:10px 18px;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none;">Set a reminder</a>' if cal else ""

    sale_date_line = f'<div style="font-size:14px;color:#7a7a7a;margin-top:8px;font-weight:500;">Sale opens {format_date_short(sale_start)}</div>' if sale_start else ""
    img_col = f'<td width="186" style="vertical-align:middle;text-align:right;padding:8px 20px 20px 12px;"><img src="{img_url}" width="156" height="118" style="display:block;object-fit:cover;object-position:center top;border-radius:16px;border:1px solid #dadfda;box-shadow:0 8px 22px rgba(17,24,39,0.05);background:#f4f4f4;" /></td>' if img_url else ""

    return f"""
    <tr>
      <td style="padding:0 0 14px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #dfe5df;border-radius:22px;"><tr>
          <td colspan="2" style="padding:22px 22px 0;"><span style="display:inline-block;font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#6b7280;">Get ready early</span></td>
        </tr><tr>
          <td style="vertical-align:top;">
            <div style="padding:10px 0 22px 22px;">
              <div style="font-size:20px;font-weight:700;letter-spacing:-0.03em;color:#1a1a1a;line-height:1.15;">{e['name']}</div>
              {sale_date_line}
              <div style="margin-top:14px;">{detail}</div>
              <div style="margin-top:18px;">{btn}{cal_btn}</div>
            </div>
          </td>
          {img_col}
        </tr></table>
      </td>
    </tr>
    """

def coming_up_rows(events_list):
    rows = ""
    for days_away, e in events_list:
        sale_start = format_date_short(e.get("sale_start", ""))
        cal = gcal_link(e["name"], e.get("sale_start", ""))
        cal_link_html = f'&nbsp;<a href="{cal}" style="font-size:11px;color:#aaa;text-decoration:none;">+ calendar</a>' if cal else ""
        rows += f"""
        <tr>
          <td style="padding:8px 0;border-bottom:0.5px solid #f5f5f5;font-size:13px;color:#1a1a1a;">{e['name']}</td>
          <td style="padding:8px 0;border-bottom:0.5px solid #f5f5f5;font-size:13px;color:#666;text-align:right;white-space:nowrap;">sale opens {sale_start} {cal_link_html}</td>
        </tr>
        """
    return rows

def section_break(label, title, description, accent, top_pad=28, anchor=""):
    anchor_html = f'<a id="{anchor}" style="display:block;position:relative;top:-8px;"></a>' if anchor else ""
    return f"""
    <tr><td style="padding:{top_pad}px 0 16px;">
      {anchor_html}
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding-bottom:10px;border-top:1px solid #ececec;"></td>
        </tr>
      </table>
      <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:{accent};margin-bottom:6px;">{label}</div>
      <div style="font-size:22px;font-weight:700;letter-spacing:-0.03em;color:#1a1a1a;">{title}</div>
      <div style="font-size:13px;color:#666;line-height:1.6;margin-top:4px;">{description}</div>
    </td></tr>"""

def build_digest_overview(has_live, has_action, has_coming, has_spotlight):
    items = []
    if has_live or has_action or has_coming or has_spotlight:
        items.append(("Tickets", "Live sales, action points, upcoming windows and a spotlight pick", "#tickets"))

    if not items:
        return ""

    rows_html = "".join(
        f"""
        <tr>
          <td style="padding:7px 0;border-bottom:0.5px solid #ececec;">
            <a href="{href}" style="font-size:13px;color:#1a1a1a;text-decoration:none;font-weight:600;">{title}</a>
          </td>
          <td style="padding:7px 0;border-bottom:0.5px solid #ececec;font-size:12px;color:#777;text-align:right;">{desc}</td>
        </tr>"""
        for title, desc, href in items
    )
    return f"""
    <tr><td style="padding:22px 0 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #dfe5df;border-radius:22px;">
        <tr>
          <td style="padding:22px 22px 10px;vertical-align:top;">
            <div style="font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#6b7280;">In this issue</div>
            <div style="font-size:18px;font-weight:700;letter-spacing:-0.03em;color:#1a1a1a;line-height:1.2;margin-top:8px;">A quick scan of what’s inside this week’s digest.</div>
          </td>
        </tr>
        <tr>
          <td style="padding:0 22px 14px;">
            <table width="100%" cellpadding="0" cellspacing="0">{rows_html}</table>
          </td>
        </tr>
      </table>
    </td></tr>"""

def spotlight_ticket_block(e):
    status_map = {
        "available": ("Tickets available", "#166534", "#ecfdf3"),
        "limited": ("Limited availability", "#9a3412", "#fff7ed"),
        "ballot": ("Ballot / registration", "#374151", "#f3f4f6"),
        "sold_out": ("Sold out", "#991b1b", "#fef2f2"),
        "free": ("Free entry", "#166534", "#ecfdf3"),
    }
    scarcity_map = {
        "good": "Good availability",
        "moderate": "Some sections going",
        "tight": "Selling fast",
        "very_tight": "Very limited",
    }
    status_key = e.get("ticket_status", "")
    scarcity_key = e.get("ticket_scarcity", "")
    note = e.get("ticket_availability_notes", "")
    if not status_key and not scarcity_key and not note:
        return ""

    status_label, status_color, status_bg = status_map.get(status_key, ("Ticket status", "#374151", "#f3f4f6"))
    scarcity_label = scarcity_map.get(scarcity_key, "")
    scarcity_html = f'<div style="font-size:12px;color:#555;margin-top:6px;"><strong style="color:#1a1a1a;">Scarcity:</strong> {scarcity_label}</div>' if scarcity_label else ""
    note_html = f'<div style="font-size:12px;color:#555;line-height:1.65;margin-top:8px;">{note}</div>' if note else ""
    return f"""
    <div style="margin:14px 0 0;padding:12px 14px;background:#fafafa;border:1px solid #ececec;border-radius:10px;">
      <span style="display:inline-block;font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{status_color};background:{status_bg};padding:4px 8px;border-radius:999px;">{status_label}</span>
      {scarcity_html}
      {note_html}
    </div>"""

def is_trial_active(user):
    # Payments not yet enabled — all users have full access
    return True

def send_digest(user_name, user_email):
    today = date.today()
    all_events = load_events()
    events = all_events

    on_sale = []
    closing_soon = []
    opening_soon = []
    action_required = []
    coming_later = []

    for e in events:
        if not e.get("sale_start"):
            continue
        sale_date = datetime.strptime(e["sale_start"], "%Y-%m-%d").date()
        days_away = (sale_date - today).days
        sale_end = e.get("sale_end")
        days_until_close = (datetime.strptime(sale_end, "%Y-%m-%d").date() - today).days if sale_end else 999

        if e.get("status") == "action_required" and e.get("notes"):
            action_required.append((days_away, e))
        elif e.get("status") == "action_required":
            # No notes yet — treat as coming_soon until notes are filled in
            if 0 < days_away <= 14:
                opening_soon.append((days_away, e))
            else:
                coming_later.append((days_away, e))
        elif e.get("status") == "on_sale" or days_away <= 0:
            if days_until_close <= 7:
                closing_soon.append((days_until_close, e))
            else:
                on_sale.append((days_away, e))
        elif 0 < days_away <= 14:
            opening_soon.append((days_away, e))
        else:
            coming_later.append((days_away, e))

    on_sale.sort(key=lambda x: x[0])
    closing_soon.sort(key=lambda x: x[0])
    opening_soon.sort(key=lambda x: x[0])
    action_required.sort(key=lambda x: x[0])
    coming_later.sort(key=lambda x: x[0])

    total = len(on_sale) + len(closing_soon) + len(opening_soon) + len(action_required) + len(coming_later)
    subject = build_subject(on_sale, closing_soon, opening_soon, action_required, today)
    intro = intro_text(on_sale, closing_soon, action_required, opening_soon)

    live_section = ""
    if on_sale or closing_soon:
        cards = "".join([live_card(e, "closing_soon") for _, e in closing_soon] + [live_card(e, "on_sale") for _, e in on_sale])
        live_section = f"""
        <tr><td style="padding:1.5rem 0 0.25rem;">
          <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#ff6a13;margin-bottom:2px;">Live now</div>
        </td></tr>
        {cards}
        """

    attention_section = ""
    if action_required:
        cards = "".join([attention_card(e) for _, e in action_required])
        attention_section = f"""
        <tr><td style="padding:1.5rem 0 0.25rem;">
          <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#ff6a13;margin-bottom:2px;">Action required</div>
        </td></tr>
        {cards}
        """

    coming_section = ""
    all_coming = opening_soon + coming_later
    if all_coming:
        rows = coming_up_rows(all_coming[:6])
        coming_section = f"""
        <tr><td style="padding:1.5rem 0 0.5rem;">
          <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#ff6a13;margin-bottom:10px;">Coming up</div>
          <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
        </td></tr>
        """

    # Spotlight section — featured card + ranked list of all spotlight events
    spotlight_pool = [e for e in all_events if e.get("spotlight") and e.get("spotlight_description")]
    overview_section = build_digest_overview(
        bool(on_sale or closing_soon),
        bool(action_required),
        bool(opening_soon or coming_later),
        bool(spotlight_pool),
    )
    spotlight_section = ""
    if spotlight_pool:
        def spotlight_sort_key(e):
            for field in ("sale_start", "event_start"):
                val = e.get(field)
                if val:
                    d = datetime.strptime(val, "%Y-%m-%d").date()
                    if d >= date.today():
                        return d
            return date(9999, 12, 31)
        sorted_spotlights = sorted(spotlight_pool, key=spotlight_sort_key)
        def days_until(e):
            for field in ("event_start", "sale_start"):
                val = e.get(field)
                if val:
                    d = datetime.strptime(val, "%Y-%m-%d").date()
                    if d >= date.today():
                        return (d - date.today()).days
            return None

        spot = sorted_spotlights[0]
        event_date_str = ""
        if spot.get("event_start"):
            days_left = days_until(spot)
            date_range = format_date_short(spot["event_start"]) + ((" – " + format_date_short(spot["event_end"])) if spot.get("event_end") else "")
            location = spot.get("location", "")
            location_html = f'<span style="color:#555;">{location}</span>&nbsp;&nbsp;·&nbsp;&nbsp;' if location and location != "TBA" else ""
            days_html = f'<span style="color:#6b7280;font-weight:600;">{days_left} days away</span>' if days_left is not None else ""
            event_date_str = f'<div style="font-size:12px;margin-top:4px;">{location_html}{date_range}&nbsp;&nbsp;{days_html}</div>'
        availability_html = spotlight_ticket_block(spot)
        btn = f'<a href="{spot["ticket_url"]}" style="display:inline-block;background:#166534;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;margin-top:14px;">More info →</a>' if spot.get("ticket_url") else ""
        image_html = f'<div style="float:right;width:150px;margin:6px 0 12px 18px;text-align:center;"><img src="{spot["image_url"]}" width="132" height="132" style="display:block;object-fit:cover;object-position:center top;border-radius:999px;border:1px solid #dbdfdc;box-shadow:0 8px 22px rgba(17,24,39,0.05);background:#f4f4f4;margin:0 auto;" /></div>' if spot.get("image_url") else ""
        featured_card = f"""
          <div style="background:#ffffff;border:1px solid #dfe5df;border-radius:22px;overflow:hidden;margin-bottom:12px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:1.6rem 1.6rem 0.3rem;vertical-align:top;">
                  <div style="font-size:20px;font-weight:700;letter-spacing:-0.03em;color:#1a1a1a;line-height:1.15;">{spot['name']}</div>
                  {event_date_str}
                </td>
              </tr>
              <tr>
                <td style="padding:0.55rem 1.6rem 1.6rem;vertical-align:top;">
                  <div style="font-size:13px;color:#4b5563;line-height:1.8;">
                    {image_html}
                    {spot['spotlight_description']}
                    {availability_html}
                    <div style="clear:both;">{btn}</div>
                  </div>
                </td>
              </tr>
            </table>
          </div>"""
        rest_rows = ""
        for s in sorted_spotlights[1:4]:
            s_date = ""
            for field in ("event_start", "sale_start"):
                val = s.get(field)
                if val:
                    s_date = format_date_short(val)
                    break
            s_btn = f'<a href="{s["ticket_url"]}" style="font-size:11px;color:#1a1a1a;text-decoration:none;">More info →</a>' if s.get("ticket_url") else ""
            rest_rows += f'<tr><td style="padding:7px 0;border-bottom:0.5px solid #ececec;font-size:13px;color:#1a1a1a;">{s["name"]}</td><td style="padding:7px 0;border-bottom:0.5px solid #ececec;font-size:12px;color:#888;text-align:right;white-space:nowrap;">{s_date}&nbsp;&nbsp;{s_btn}</td></tr>'
        rest_table = f'<table width="100%" cellpadding="0" cellspacing="0">{rest_rows}</table>' if rest_rows else ""
        spotlight_section = f"""
        <tr><td style="padding:1.5rem 0 0;">
          <a id="spotlight" style="display:block;position:relative;top:-8px;"></a>
          <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#ff6a13;margin-bottom:4px;">Spotlight</div>
          <div style="font-size:12px;color:#888;margin-bottom:12px;">The events that feel more interesting than the obvious picks.</div>
          {featured_card}
          {rest_table}
        </td></tr>
        """

    html = f"""
    <html><head>
    <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">
    </head><body style="font-family:'Helvetica Neue',Arial,sans-serif;background:#f5f5f3;margin:0;padding:1.5rem;">
    <div style="max-width:540px;margin:0 auto;background:#fff;">

      <div style="height:6px;background:#ff6a13;"></div>
      <div style="padding:1.35rem 2rem 1.25rem;border-bottom:1px solid #ece8e1;background:linear-gradient(180deg,#fff8f2 0%,#ffffff 100%);">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="vertical-align:middle;">
            <table cellpadding="0" cellspacing="0"><tr>
              <td width="46" style="vertical-align:middle;padding-right:10px;">
                <img src="https://coenvanrappard-lgtm.github.io/Fluitsignaal/logo.png" width="36" height="36" alt="Fluitsignaal logo" style="display:block;width:36px;height:36px;object-fit:contain;" />
              </td>
              <td style="vertical-align:middle;">
                <div style="font-family:'DM Serif Display',Georgia,serif;font-size:27px;line-height:1;color:#1a1a1a;letter-spacing:-0.03em;">Fluitsignaal</div>
                <div style="font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#ff6a13;margin-top:6px;">Weekly ticket digest</div>
              </td>
            </tr></table>
          </td>
          <td style="text-align:right;font-size:12px;color:#8c8c8c;vertical-align:middle;">
            <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#b26b3c;margin-bottom:5px;">Edition</div>
            <div>Weekly update — {today.strftime('%d %B')}</div>
          </td>
        </tr></table>
      </div>

      <div style="padding:1.25rem 2rem;border-bottom:0.5px solid #ebebeb;background:#fafafa;">
        <div style="font-size:13px;font-weight:600;color:#1a1a1a;margin-bottom:5px;">Hi {user_name.split()[0]}, here's what matters this week</div>
        <div style="font-size:13px;color:#555;line-height:1.7;">{intro}</div>
      </div>

      <div style="padding:0 2rem 2rem;">
        <table width="100%" cellpadding="0" cellspacing="0">
          {overview_section}
          {section_break("Tickets", "Ticket alerts", "The sales that are live, approaching, or worth preparing for before the window opens.", "#ff6a13", 24, "tickets") if (live_section or attention_section or coming_section or spotlight_section) else ""}
          {live_section}
          {attention_section}
          {coming_section}
          {spotlight_section}
          {'<tr><td style="padding:3rem 0;text-align:center;color:#bbb;font-size:14px;">Nothing to report this week.</td></tr>' if total == 0 else ''}
        </table>
      </div>

      <div style="padding:1.25rem 2rem;border-top:0.5px solid #ebebeb;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="font-size:11px;color:#bbb;line-height:1.6;">You're receiving this because you subscribed to Fluitsignaal ticket alerts.<br><a href="https://fluitsignaal.com/dashboard.html?email={quote(user_email)}" style="font-size:11px;color:#ff6a13;text-decoration:none;">Manage preferences</a></td>
          <td style="text-align:right;vertical-align:top;"><a href="https://fluitsignaal.com" style="font-size:11px;color:#ff6a13;text-decoration:none;white-space:nowrap;">fluitsignaal.com →</a></td>
        </tr></table>
      </div>

    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = user_email
    msg["Message-ID"] = f"<{uuid.uuid4()}@fluitsignaal>"
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, user_email, msg.as_string())
    print(f"Digest sent to {user_email}")

if __name__ == "__main__":
    for user in load_users():
        if not is_trial_active(user):
            print(f"Trial expired for {user['email']}, skipping")
            continue
        if user.get("email"):
            send_digest(user["name"], user["email"])
