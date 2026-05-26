from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify
)

import requests
from requests.exceptions import SSLError
import urllib3
import xml.etree.ElementTree as ET
import os
import sqlite3
from functools import wraps

app = Flask(__name__)

# =========================
# CONFIG
# =========================

app.secret_key = os.getenv("ABK_SECRET_KEY", os.getenv("SECRET_KEY", "change_me"))

ADMIN_USER = os.getenv("ABK_ADMIN_USER", os.getenv("ADMIN_USER", "admin"))
ADMIN_PASSWORD = os.getenv("ABK_ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", "admin"))

XML_URLS = [
    url.strip()
    for url in os.getenv("BC_PHONEBOOKS", os.getenv("PHONEBOOK_URLS", "")).split(",")
    if url.strip()
]

VERIFY_PHONEBOOK_SSL = os.getenv("ABK_VERIFY_PHONEBOOK_SSL", "true").lower() in ["1", "true", "yes"]

DB_FILE = "phonebook.db"

# =========================
# DATABASE
# =========================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS phonebook_settings (
            phone TEXT PRIMARY KEY,
            color TEXT DEFAULT '',
            note TEXT DEFAULT '',
            hidden INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS global_settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()

init_db()


def get_setting(key, default=None):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM global_settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return default
    return row[0]


def set_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO global_settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()

# =========================
# AUTH
# =========================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# =========================
# HELPERS
# =========================

def load_settings():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()
    cur.execute("SELECT * FROM phonebook_settings")

    data = {}

    for row in cur.fetchall():
        data[row["phone"]] = {
            "color": row["color"],
            "note": row["note"],
            "hidden": row["hidden"]
        }

    conn.close()
    return data


def save_setting(phone, color, note, hidden):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO phonebook_settings(phone, color, note, hidden)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(phone)
        DO UPDATE SET
            color=excluded.color,
            note=excluded.note,
            hidden=excluded.hidden
    """, (phone, color, note, hidden))

    conn.commit()
    conn.close()


def reset_setting(phone):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("DELETE FROM phonebook_settings WHERE phone = ?", (phone,))

    conn.commit()
    conn.close()


def load_phonebook():
    entries = []
    errors = []

    settings = load_settings()

    for url in XML_URLS:
        try:
            verify = VERIFY_PHONEBOOK_SSL
            try:
                response = requests.get(url, timeout=10, verify=verify)
            except SSLError:
                if verify:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    response = requests.get(url, timeout=10, verify=False)
                else:
                    raise

            response.raise_for_status()

            root = ET.fromstring(response.content)

            for entry in root.findall("DirectoryEntry"):
                name = entry.findtext("Name", default="")
                phone = entry.findtext("Telephone", default="")

                setting = settings.get(phone, {})

                item = {
                    "name": name,
                    "phone": phone,
                    "source": url,
                    "color": setting.get("color", ""),
                    "note": setting.get("note", ""),
                    "hidden": setting.get("hidden", 0)
                }

                entries.append(item)

        except Exception as e:
            errors.append(f"{url}: {e}")

    entries.sort(key=lambda x: x["name"].lower())

    return entries, errors


def matches_query(item, query):
    if not query:
        return True

    normalized_query = str(query).strip().lower()
    haystack = " ".join(
        str(item.get(field, "") or "").strip().lower()
        for field in ("name", "phone", "note", "source")
    )
    return normalized_query in haystack


# =========================
# API
# =========================

@app.route("/api/search")
def api_search():
    search_query = request.args.get("q", "").strip()
    entries, _ = load_phonebook()

    # veřejný výpis -> skryté nezobrazovat
    entries = [x for x in entries if not x["hidden"]]
    if search_query:
        entries = [x for x in entries if matches_query(x, search_query)]

    return jsonify(entries)


@app.route("/api/admin/search")
@login_required
def api_admin_search():
    search_query = request.args.get("q", "").strip()
    entries, _ = load_phonebook()

    if search_query:
        entries = [x for x in entries if matches_query(x, search_query)]

    return jsonify(entries)


@app.route("/api/admin/reset", methods=["POST"])
@login_required
def api_admin_reset():
    data = request.get_json()
    phone = data.get("phone", "").strip()

    if not phone:
        return jsonify({"error": "Missing phone"}), 400

    reset_setting(phone)
    return jsonify({"success": True})


@app.route("/api/admin/save", methods=["POST"])
@login_required
def api_admin_save():
    data = request.get_json()
    phone = data.get("phone", "").strip()
    color = data.get("color", "").strip()
    note = data.get("note", "").strip()
    hidden = data.get("hidden", 0)

    if not phone:
        return jsonify({"error": "Missing phone"}), 400

    save_setting(phone, color, note, hidden)
    return jsonify({"success": True})


@app.route("/api/admin/save_bulk", methods=["POST"])
@login_required
def api_admin_save_bulk():
    data = request.get_json() or {}
    items = data.get("items")

    if not items or not isinstance(items, list):
        return jsonify({"error": "Missing items"}), 400

    for it in items:
        phone = str(it.get("phone", "")).strip()
        if not phone:
            continue
        color = str(it.get("color", "")).strip()
        note = str(it.get("note", "")).strip()
        hidden = int(it.get("hidden", 0)) if it.get("hidden") is not None else 0
        save_setting(phone, color, note, hidden)

    return jsonify({"success": True})


@app.route("/api/admin/announcement", methods=["POST"])
@login_required
def api_admin_announcement():
    data = request.get_json() or {}
    text = data.get('text', '')
    ann_type = data.get('type', 'info')
    enabled = 1 if data.get('enabled') else 0

    set_setting('announcement_text', text)
    set_setting('announcement_type', ann_type)
    set_setting('announcement_enabled', str(enabled))

    return jsonify({'success': True})


# =========================
# PUBLIC
# ========================= 

@app.route("/")
def index():
    search_query = request.args.get("q", "").strip()
    entries, errors = load_phonebook()

    # veřejný výpis -> skryté nezobrazovat
    entries = [x for x in entries if not x["hidden"]]
    if search_query:
        entries = [x for x in entries if matches_query(x, search_query)]

    announcement_text = get_setting('announcement_text', '') or ''
    announcement_type = get_setting('announcement_type', 'info') or 'info'
    announcement_enabled = int(get_setting('announcement_enabled', '0') or 0)

    announcement = {
        'text': announcement_text,
        'type': announcement_type,
        'enabled': announcement_enabled
    }

    return render_template("index.html", entries=entries, errors=errors, announcement=announcement)

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin"))
        else:
            error = "Neplatné přihlášení"

    return render_template("login.html", error=error)

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# =========================
# ADMIN
# =========================

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    search_query = request.args.get("q", "").strip()

    if request.method == "POST":

        phone = request.form.get("phone")
        color = request.form.get("color", "")
        note = request.form.get("note", "")
        hidden = 1 if request.form.get("hidden") else 0

        save_setting(phone, color, note, hidden)

        return redirect(url_for("admin", q=search_query) if search_query else url_for("admin"))

    entries, errors = load_phonebook()
    if search_query:
        entries = [x for x in entries if matches_query(x, search_query)]

    # load announcement settings
    announcement_text = get_setting('announcement_text', '') or ''
    announcement_type = get_setting('announcement_type', 'info') or 'info'
    announcement_enabled = int(get_setting('announcement_enabled', '0') or 0)

    announcement = {
        'text': announcement_text,
        'type': announcement_type,
        'enabled': announcement_enabled
    }

    return render_template("admin.html", entries=entries, errors=errors, announcement=announcement)

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app.run(debug=True)