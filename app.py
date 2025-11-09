# app.py
# -*- coding: utf-8 -*-
import re
import os
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
import pytz
import gspread
from google.oauth2.service_account import Credentials

# רשימת תחומים
SPECIALIZATIONS = [
    "רווחה", "מוגבלות", "זקנה", "ילדים ונוער", "בריאות הנפש",
    "שיקום", "משפחה", "נשים", "בריאות", "קהילה"
]

COLUMNS_ORDER = [
    "תאריך שליחה", "שם פרטי", "שם משפחה", "סטטוס מדריך", "מוסד", "תחום התמחות",
    "רחוב", "עיר", "מיקוד", "מספר סטודנטים שניתן לקלוט (1 או 2)",
    "מעוניין להמשיך", "בקשות מיוחדות", "חוות דעת - נקודות",
    "חוות דעת - טקסט חופשי", "טלפון", "אימייל"
]

app = Flask(__name__)
app.secret_key = "secret-key-change-me"

def get_worksheet():
    """
    חיבור ל-Google Sheets באמצעות משתני סביבה:
    GOOGLE_SERVICE_ACCOUNT_JSON - תוכן מלא של קובץ החשבון השירות (JSON)
    SPREADSHEET_ID - ה-ID של הגיליון
    """
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise RuntimeError("Missing GOOGLE_SERVICE_ACCOUNT_JSON env var")

    sheet_id = os.environ.get("SPREADSHEET_ID")
    if not sheet_id:
        raise RuntimeError("Missing SPREADSHEET_ID env var")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id).sheet1

def ensure_header(ws):
    existing = ws.get_all_values()
    if not existing or existing[0] != COLUMNS_ORDER:
        ws.clear()
        ws.append_row(COLUMNS_ORDER)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.form
        errors = []

        if not f.get("first_name"):
            errors.append("יש למלא שם פרטי")
        if not f.get("last_name"):
            errors.append("יש למלא שם משפחה")
        if f.get("specialization") == "בחר/י מהרשימה":
            errors.append("יש לבחור תחום התמחות")

        phone = f.get("phone", "").replace("-", "").replace(" ", "")
        if not re.match(r"^(0?5\d{8})$", phone):
            errors.append("מספר טלפון לא תקין (דוגמה: 0501234567)")

        email = f.get("email", "")
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("כתובת דוא\"ל לא תקינה")

        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("index"))

        tz = pytz.timezone("Asia/Jerusalem")
        record = {
            "תאריך שליחה": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
            "שם פרטי": f.get("first_name", ""),
            "שם משפחה": f.get("last_name", ""),
            "סטטוס מדריך": f.get("mentor_status", ""),
            "מוסד": f.get("institute", ""),
            "תחום התמחות": f.get("specialization", ""),
            "רחוב": f.get("street", ""),
            "עיר": f.get("city", ""),
            "מיקוד": f.get("postal_code", ""),
            "מספר סטודנטים שניתן לקלוט (1 או 2)": int(f.get("num_students", 1)),
            "מעוניין להמשיך": f.get("continue_mentoring", ""),
            "בקשות מיוחדות": f.get("special_requests", ""),
            "חוות דעת - נקודות": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת - טקסט חופשי": f.get("mentor_feedback_text", ""),
            "טלפון": phone,
            "אימייל": email
        }

        try:
            ws = get_worksheet()
            ensure_header(ws)
            ws.append_row([record[c] for c in COLUMNS_ORDER])
            flash("✅ הטופס נשלח ונשמר בהצלחה!", "success")
        except Exception as e:
            print("Error saving to Google Sheets:", e)
            flash("❌ שגיאה בשמירה לגיליון.", "error")

        return redirect(url_for("index"))

    return render_template("index.html", specializations=SPECIALIZATIONS)

if __name__ == "__main__":
    app.run(debug=True)
