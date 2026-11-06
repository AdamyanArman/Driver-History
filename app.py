import os
import json
import io
from datetime import datetime
from functools import wraps

import requests
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
)
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

from dotenv import load_dotenv
from werkzeug.security import check_password_hash
from cryptography.fernet import Fernet


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "fallback_default_secret_key")


encryption_key = os.getenv("ENCRYPTION_KEY")
cipher_suite = Fernet(encryption_key.encode()) if encryption_key else None


def decrypt_data(encrypted_text):
    if not cipher_suite or not encrypted_text:
        return None
    try:
        return cipher_suite.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        print("Ապակոդավորման սխալ:", e)
        return None



WEB_USERNAME = os.getenv("WEB_USERNAME")
WEB_PASSWORD_HASH = os.getenv("WEB_PASSWORD_HASH")


LOGIN_URL = decrypt_data(os.getenv("LOGIN_URL"))
HISTORY_URL = decrypt_data(os.getenv("HISTORY_URL"))


encrypted_drivers_json = os.getenv("DRIVERS_JSON", "")
decrypted_drivers_json = decrypt_data(encrypted_drivers_json)

try:
    if decrypted_drivers_json:
        DRIVERS_RAW = json.loads(decrypted_drivers_json)
        DRIVERS = {int(k): v for k, v in DRIVERS_RAW.items()}
    else:
        DRIVERS = {}
except json.JSONDecodeError:
    print("Սխալ՝ ապակոդավորված JSON-ը վավեր չէ")
    DRIVERS = {}

DRIVER_CHOICES = {
    "Armen": 1,
    "Davit": 2,
    "Syoma": 3,
    "Hayk": 4,
    "Karen": 5,
    "Seroj": 6
}



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Ստուգում ենք մուտքանունը և համեմատում գաղտնաբառը ՀԵՇԻ հետ
        if WEB_USERNAME and WEB_PASSWORD_HASH and username == WEB_USERNAME and check_password_hash(WEB_PASSWORD_HASH,
                                                                                                   password):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Սխալ մուտքանուն կամ գաղտնաբառ"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    drivers_list = list(DRIVER_CHOICES.keys())
    orders = None
    delivery_counts = {}
    total_deliveries = 0
    selected_driver = None
    from_date = ""
    to_date = ""
    error = None

    if request.method == "POST":
        selected_driver = request.form.get("driver")
        from_date = request.form.get("from_date", "").strip()
        to_date = request.form.get("to_date", "").strip()

        if not selected_driver or selected_driver not in DRIVER_CHOICES:
            error = "Խնդրում ենք ընտրել վարորդ"
        elif not from_date or not to_date:
            error = "Խնդրում ենք ընտրել ամսաթվերի միջակայք"
        else:
            try:
                # Convert HTML date (YYYY-MM-DD) to API format (DD-MM-YYYY)
                from_api = datetime.strptime(from_date, "%Y-%m-%d").strftime("%d-%m-%Y")
                to_api = datetime.strptime(to_date, "%Y-%m-%d").strftime("%d-%m-%Y")

                driver_id = DRIVER_CHOICES[selected_driver]

                # Ստանում ենք վարորդի լոգինը և գաղտնաբառը ապակոդավորված DRIVERS բառարանից
                driver_data = DRIVERS.get(driver_id, {})
                login_api = driver_data.get("login")
                password_api = driver_data.get("password")

                if not LOGIN_URL or not HISTORY_URL or not login_api or not password_api:
                    error = "Խնդիր կա: URL-ները կամ վարորդի տվյալները բացակայում են (ստուգեք գաղտնագրումը .env-ում)"
                else:
                    # Login
                    login_data = {
                        "login_auth": login_api,
                        "pass_auth": password_api,
                    }
                    login_headers = {"lang": "rus"}

                    login_response = requests.post(
                        LOGIN_URL,
                        headers=login_headers,
                        data=login_data,
                        timeout=30,
                    )
                    login_response.raise_for_status()
                    login_result = login_response.json()
                    token = login_result["data"]["token"]

                    # History
                    history_headers = {
                        "lang": "hy",
                        "Auth": f"Bearer {token}",
                    }
                    history_data = {
                        "fromdate": from_api,
                        "todate": to_api,
                        "offset": "0",
                        "limit": "1000",
                    }

                    history_response = requests.post(
                        HISTORY_URL,
                        headers=history_headers,
                        data=history_data,
                        timeout=60,
                    )
                    history_response.raise_for_status()
                    history_result = history_response.json()
                    orders = history_result.get("data", [])

                    # Count delivery prices
                    for order in orders:
                        price = order.get("delivery_price")
                        if price is not None:
                            delivery_counts[price] = delivery_counts.get(price, 0) + 1

                    total_deliveries = sum(delivery_counts.values())

                    # Store in session for export
                    session["last_orders"] = orders
                    session["last_delivery_counts"] = delivery_counts
                    session["last_total"] = total_deliveries
                    session["last_driver"] = selected_driver
                    session["last_from"] = from_date
                    session["last_to"] = to_date

            except requests.exceptions.RequestException as e:
                error = f"API սխալ: {str(e)}"
            except Exception as e:
                error = f"Սխալ: {str(e)}"

    return render_template(
        "dashboard.html",
        drivers=drivers_list,
        orders=orders,
        delivery_counts=delivery_counts,
        total_deliveries=total_deliveries,
        selected_driver=selected_driver,
        from_date=from_date,
        to_date=to_date,
        error=error,
    )


@app.route("/export")
@login_required
def export():
    orders = session.get("last_orders")
    delivery_counts = session.get("last_delivery_counts", {})
    total_deliveries = session.get("last_total", 0)
    driver_name = session.get("last_driver", "driver")
    from_date = session.get("last_from", "")
    to_date = session.get("last_to", "")

    if not orders:
        flash("Տվյալներ չկան արտահանելու համար։ Նախ որոնեք։", "error")
        return redirect(url_for("dashboard"))


    wb = Workbook()
    ws = wb.active
    ws.title = "Order History"


    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="FF001F", end_color="FF001F", fill_type="solid")
    title_font = Font(bold=True, size=14, color="FF001F")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    center_align = Alignment(horizontal="center", vertical="center")


    ws.merge_cells("A1:C1")
    ws["A1"] = f"Վարորդ՝ {driver_name} | {from_date} — {to_date}"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")


    headers = ["ID", "Առաքման արժեք", "Ամսաթիվ"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border


    for row_idx, order in enumerate(orders, 4):
        ws.cell(row=row_idx, column=1, value=order.get("id")).border = thin_border
        ws.cell(row=row_idx, column=2, value=order.get("delivery_price")).border = thin_border
        ws.cell(row=row_idx, column=3, value=order.get("adddate")).border = thin_border


    summary_start = 4 + len(orders) + 2

    ws.cell(row=summary_start, column=1, value="Ամփոփում").font = Font(bold=True, size=12)

    ws.cell(row=summary_start + 1, column=1, value="Առաքման արժեք").font = Font(bold=True)
    ws.cell(row=summary_start + 1, column=2, value="Քանակ").font = Font(bold=True)
    ws.cell(row=summary_start + 1, column=1).fill = PatternFill(start_color="354054", end_color="354054",
                                                                fill_type="solid")
    ws.cell(row=summary_start + 1, column=2).fill = PatternFill(start_color="354054", end_color="354054",
                                                                fill_type="solid")
    ws.cell(row=summary_start + 1, column=1).font = Font(bold=True, color="FFFFFF")
    ws.cell(row=summary_start + 1, column=2).font = Font(bold=True, color="FFFFFF")

    for i, (price, count) in enumerate(sorted(delivery_counts.items())):
        ws.cell(row=summary_start + 2 + i, column=1, value=price)
        ws.cell(row=summary_start + 2 + i, column=2, value=count)

    total_row = summary_start + 2 + len(delivery_counts) + 1
    ws.cell(row=total_row, column=1, value="Ընդհանուր առաքումներ").font = Font(bold=True)
    ws.cell(row=total_row, column=2, value=total_deliveries).font = Font(bold=True)

    # Column widths
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 25

    # Freeze
    ws.freeze_panes = "A4"

    # Save to memory
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"driver_history_{driver_name}_{from_date}_{to_date}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)