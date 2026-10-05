import os
import re
import logging
import smtplib
import requests
import gspread
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import logger_config

load_dotenv()
logger_config.setup_logging()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_gspread_client():
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials/google_service_account.json")
    creds_path = Path(creds_file)

    if not creds_path.exists():
        send_error_email(
            subject="[Birthday Bot] 📢❗🚨 FAILURE 📢❗🚨 - Goodle Credential File Error",
            body=(
                f"Google credentials file not found: {creds_path}"
            )
        )
        raise FileNotFoundError(f"Google credentials file not found: {creds_path}")

    credentials = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    return gspread.authorize(credentials)

def load_sheet_as_dataframe(sheet_id) -> pd.DataFrame:
    """Connects to Google Sheets and pulls the first tab data."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.get_worksheet(0)
        return pd.DataFrame(worksheet.get_all_records())

    except Exception as e:
        logging.error(f"Error reading Google Sheet ID {sheet_id}: {e}")
        return pd.DataFrame() # Return empty dataframe on error

def clean_phone(number):
    """
    Formating function tailored for Meta API syntax constraints.
    Meta expects ONLY digits, starting with country code (e.g., '94771234567' for SL).
    No '+' sign, no special characters, no spaces.
    """
    if pd.isna(number) or str(number).strip() in ("", "nan", "None"):
        return None

    # Strip everything except digits
    digits = re.sub(r"\D", "", str(number).strip())

    if not digits or digits.startswith("011"): # Skip missing entries or local landlines
        return None

    # Format logic for Sri Lankan numbers (+94)
    if digits.startswith("0"):
        digits = "94" + digits[1:]
    elif digits.startswith("94"):
        pass
    elif len(digits) == 9:
        digits = "94" + digits
    else:
        return None # Return None if format doesn't look like a standard mobile number

    return digits if len(digits) <= 12 else None

def get_best_phone(row):
    """Prefer Mobile -> Home -> Additional"""
    for col in ["Mobile Phone", "Home Phone", "Additional Phone"]:
        phone = clean_phone(row[col])
        if phone:
            return phone
    return None

def parse_birthday(val):
    """Return a date object or None if invalid"""
    if pd.isna(val):
        return None

    #Already a datetime/ date
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val

    s = str(val).strip()
    if s.startswith("#") or s.lower() in ("nan", "none", ""):
        return None

    try:
        return pd.to_datetime(s, dayfirst=True).date()
    except Exception:
        return None

def load_members_from_sheet() -> tuple[list, str | None]:
    """
    Load members from Google Sheet tab: members
    """
    members_filename = os.getenv("MEMBERS_GOOGLE_SHEET_ID")

    try:
        df = load_sheet_as_dataframe(members_filename)
        members = []

        for _, row in df.iterrows():
            id = str(row.get("Customer ID", "")).strip()
            if not id or len(id) == 0:
                continue

            name = str(row.get("Name", "")).strip()
            if not name or name.lower() == "nan":
                continue

            email = str(row.get("Email", "")).strip()
            if email.lower() in ("nan", "none", ""):
                email = None

            phone = get_best_phone(row)
            birthday = parse_birthday(row.get("Date of Birth"))

            # Keep only people who have at least one contact method
            if email or phone:
                members.append({
                    "id" : id,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "birthday": birthday
                })
        logging.info(f"Extracted {len(members)} members from Excel file")
        return members, None

    except Exception as e:
        error_msg = f"Failed to load members from Google Sheet: {e}"
        logging.error(error_msg)
        return [], error_msg

def load_admins() -> tuple[list, str | None]:
    """
    Load admin team from Google sheet
    Returns: (admins_list, error_message)
    """
    admin_file_name = os.getenv("ADMINS_GOOGLE_SHEET_ID")

    try:
        df = load_sheet_as_dataframe(admin_file_name)
        admins = []

        for _, row in df.iterrows():
            name = str(row.get("Name", "")).strip()
            email = str(row.get("Email", "")).strip()
            phone = clean_phone(row.get("Phone"))

            if email.lower() in ("nan", "none", ""):
                email = None

            if name and (email or phone):
                admins.append({
                    "name": name,
                    "email": email,
                    "phone": phone
                })

        logging.info(f"Loaded {len(admins)} admins")
        return admins, None

    except Exception as e:
        error_msg = f"Failed to read admins.xlsx\n\nError: {e}"
        logging.error(error_msg)
        return [], error_msg

def get_tomorrow_birthdays(members: list) -> list:
    """
    Return members whose birthday is tomorrow (month + day only).
    """
    tomorrow = date.today() + timedelta(days=1)

    result = []
    for member in members:
        bday = member.get("birthday")
        if bday and bday.month == tomorrow.month and bday.day == tomorrow.day:
            result.append(member)

    return result

def build_tomorrow_message_for_email(birthdays: list) -> str:
    """Message for tomorrow's birthdays"""
    if not birthdays:
        return ""

    lines = []
    for m in birthdays:
        bday = m["birthday"].strftime("%d %B") if m.get("birthday") else "N/A"
        lines.append(f"🎂 {m['name']}  —  {bday}")

    if len(birthdays) == 1:
        intro = "🎂Birthday Alert:"
    else:
        intro = f"There are *{len(birthdays)} members* with birthdays tomorrow:"

    message = (
            "🎉 *Birthday Reminder* 🎉\n\n"
            "Hello EXCO Team,\n\n"
            f"{intro}\n\n"
            + "\n".join(lines)
            + "\n\n"
              "📝 Please plan accordingly and let's make the day special!🎈\n\n"
              "————————————\n"
              "🤖 Automated Birthday Notification System"
    )
    return message

def send_email_to_admins(admins: list, subject: str, body: str) -> dict:
    """
    Send the same notification to all admins.
    Returns summary: {"sent": X, "failed": Y}
    """
    sent = 0
    failed = 0

    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not sender_email or not sender_password:
        logging.error("EMAIL_ADDRESS or EMAIL_PASSWORD not set in .env")
        return {"sent": 0, "failed": len(admins)}

    for admin in admins:
        to_email = admin.get("email")
        if not to_email:
            logging.warning(f"No email for admin: {admin.get('name')}")
            failed += 1
            continue

        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            logging.info(f"Notification sent to {admin['name']} <{to_email}>")
            sent += 1

        except Exception as e:
            logging.error(f"Failed to send to {admin['name']}: {e}")
            failed += 1

    return {"sent": sent, "failed": failed}

def send_error_email(subject: str, body: str) -> bool:
    """
    Send error alert email to developer.
    """
    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")
    alert_to = os.getenv("ALERT_EMAIL", "anu.isuru91@gmail.com")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not sender_email or not sender_password or not alert_to:
        logging.error("Email alert not configured in .env")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = alert_to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        logging.info(f"Error alert email sent to {alert_to}")
        return True

    except Exception as e:
        logging.error(f"Failed to send error alert email: {e}")
        return False

def create_status_report():
    status_report_sheet_id = os.getenv("STATUS_REPORT_SHEET_ID")
    if not status_report_sheet_id:
        logging.error("STATUS_REPORT_SHEET_ID is not set in .env")
        return None

    ws_name = datetime.today().strftime("%Y%m")

    try:
        logging.info(f"Opening status report spreadsheet (ID: {status_report_sheet_id})")
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(status_report_sheet_id)
        logging.info(f"Spreadsheet opened. Looking for worksheet: {ws_name}")

        try:
            ws = spreadsheet.worksheet(ws_name)
            logging.info(f"Found existing worksheet: {ws_name}")
            return ws

        except gspread.WorksheetNotFound:
            logging.info(f"Worksheet '{ws_name}' not found → creating it")
            ws = spreadsheet.add_worksheet(title=ws_name, rows=500, cols=20)
            ws_headers = [
                "logged_date", "logged_time", "members_total",
                "admin_total", "tomorrow_bdays_total", "email_sent", "email_failed"
            ]
            ws.insert_row(ws_headers, 1)
            logging.info(f"Created worksheet '{ws_name}' with headers")
            return ws

    except Exception as e:
        logging.error(f"Failed inside create_status_report: {type(e).__name__}: {e}")
        return None

def record_states(members_total, admin_total,tomorrow_bdays_total, email_sent, email_failed):
    logged_date = datetime.today().strftime("%Y-%m-%d")
    logged_time = datetime.now().strftime("%H:%M:%S")
    data_to_record = [logged_date, logged_time, members_total, admin_total, tomorrow_bdays_total, email_sent, email_failed]

    try:
        logging.info(f"Record states: {data_to_record}")
        ws = create_status_report()
        ws.append_row(data_to_record)
    except Exception as e:
        logging.error(f"Failed to record states: {e}")

if __name__ == "__main__":
    try:
        members, member_error = load_members_from_sheet()
        admins, admin_error = load_admins()

        if member_error or admin_error:
            error_text = member_error or admin_error
            logging.error(error_text)
            send_error_email(
                subject="[Birthday Bot] 📢❗🚨 FAILED -  could not load data 📢❗🚨",
                body=error_text
            )
            record_states("error", "error", "-", "-", "-")
            raise SystemExit(1)

        tomorrow_list = get_tomorrow_birthdays(members)

        if not tomorrow_list:
            logging.info("No birthdays tomorrow. No WhatsApp sent.")
            record_states(f"{len(members)}", f"{len(admins)}", "-", "-", "-" )
            logging.info("===== Birthday Notifier run finished OK =====")
            raise SystemExit(0)

        logging.info(
            "Tomorrow's birthdays: " + ", ".join(m["name"] for m in tomorrow_list)
        )

        email_body = build_tomorrow_message_for_email(tomorrow_list)

        subject = "Reminder: 🎂🎈🎉🥳 Birthday(s) Tomorrow"
        body = email_body
        email_result = send_email_to_admins(admins, subject, body)
        record_states(f"{len(members)}", f"{len(admins)}", f"{len(tomorrow_list)}", f"{email_result['sent']}", f"{email_result['failed']}" )
        logging.info(f"Email notification finished. → Sent: {email_result['sent']}, Failed: {email_result['failed']}")

        # Alert only if something failed
        if email_result["failed"] > 0:
            send_error_email(
                subject="[Birthday Bot] 📢❗🚨PARTIAL FAILURE - Email send issue📢❗🚨",
                body=(
                    f"There is a error in sending notifications.\n\n"
                    f"Sent: Emails - {email_result['sent']}\n"
                    f"Failed: Emails - {email_result['failed']}\n"
                    f"Birthdays: {', '.join(m['name'] for m in tomorrow_list)}\n"
                    f"Please check logs for details."
                )
            )
            raise SystemExit(1)

        logging.info("===== Birthday Notifier run finished OK =====")

    except SystemExit:
        raise

    except Exception as e:
        logging.exception("Unexpected crash")
        send_error_email(
            subject="[Birthday Bot] CRASHED",
            body=f"Unexpected error:\n\n{e}"
        )
        raise

