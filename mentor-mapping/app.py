# app.py
# -*- coding: utf-8 -*-
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import pytz
import gspread
from google.oauth2.service_account import Credentials

# רשימת תחומים
SPECIALIZATIONS = ["רווחה","מוגבלות","זקנה","ילדים ונוער","בריאות הנפש",
                   "שיקום","משפחה","נשים","בריאות","קהילה"]

COLUMNS_ORDER = [
    "תאריך שליחה","שם פרטי","שם משפחה","סטטוס מדריך","מוסד","תחום התמחות",
    "רחוב","עיר","מיקוד","מספר סטודנטים שניתן לקלוט (1 או 2)",
    "מעוניין להמשיך","בקשות מיוחדות","חוות דעת - נקודות",
    "חוות דעת - טקסט חופשי","טלפון","אימייל"
]

app = Flask(__name__)
app.secret_key = "secret-key-change-me"

def get_worksheet():
    import json, os
    with open("credentials.json", "r", encoding="utf-8") as f:
        creds_dict = json.load(f)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    with open("config.json", "r", encoding="utf-8") as f:
        sheet_id = json.load(f)["spreadsheet_id"]
    return gc.open_by_key(sheet_id).sheet1

def ensure_header(ws):
    existing = ws.get_all_values()
    if not existing or existing[0] != COLUMNS_ORDER:
        ws.clear()
        ws.append_row(COLUMNS_ORDER)

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        f = request.form
        errors = []
        if not f["first_name"]: errors.append("יש למלא שם פרטי")
        if not f["last_name"]: errors.append("יש למלא שם משפחה")
        if f["specialization"] == "בחר/י מהרשימה": errors.append("יש לבחור תחום התמחות")

        phone = f["phone"].replace("-","").replace(" ","")
        if not re.match(r"^(0?5\d{8})$", phone):
            errors.append("מספר טלפון לא תקין (דוגמה: 0501234567)")

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", f["email"]):
            errors.append("כתובת דוא\"ל לא תקינה")

        if errors:
            for e in errors: flash(e, "error")
            return redirect(url_for("index"))

        tz = pytz.timezone("Asia/Jerusalem")
        record = {
            "תאריך שליחה": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
            "שם פרטי": f["first_name"], "שם משפחה": f["last_name"],
            "סטטוס מדריך": f["mentor_status"], "מוסד": f["institute"],
            "תחום התמחות": f["specialization"], "רחוב": f["street"],
            "עיר": f["city"], "מיקוד": f["postal_code"],
            "מספר סטודנטים שניתן לקלוט (1 או 2)": int(f["num_students"]),
            "מעוניין להמשיך": f.get("continue_mentoring",""),
            "בקשות מיוחדות": f.get("special_requests",""),
            "חוות דעת - נקודות": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת - טקסט חופשי": f.get("mentor_feedback_text",""),
            "טלפון": phone, "אימייל": f["email"]
        }

        try:
            ws = get_worksheet()
            ensure_header(ws)
            ws.append_row([record[c] for c in COLUMNS_ORDER])
            flash("✅ הטופס נשלח ונשמר בהצלחה!", "success")
        except Exception as e:
            flash("❌ שגיאה בשמירה לגיליון.", "error")
            print(e)

        return redirect(url_for("index"))

    return render_template("index.html", specializations=SPECIALIZATIONS)

if __name__ == "__main__":
    app.run(debug=True)
