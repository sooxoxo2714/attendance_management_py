from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = '任意の暗号鍵を入れてね'

DB = "attendance.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, common_wage INTEGER)")
    c.execute("INSERT OR IGNORE INTO settings (id, common_wage) VALUES (1, 1230)")
    c.execute("""CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, date TEXT,
        start_time TEXT, end_time TEXT, minutes INTEGER
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS auth (id INTEGER PRIMARY KEY, password TEXT)")
    c.execute("SELECT COUNT(*) FROM auth")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO auth (id, password) VALUES (1, 'password')")

    conn.commit(); conn.close()

init_db()

@app.before_request
def check_login():
    allowed = ['login', 'manage_pw', 'update_password', 'db_admin', 'update_db_all', 'delete_db_row', 'update_all_bulk','static', 'allow_db_admin']
    if not session.get('logged_in') and request.endpoint not in allowed:
        return redirect(url_for('login'))

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=365)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        input_pw = request.form.get("password", "").strip()

        if input_pw == "passchange":
            session['allow_change'] = True
            return redirect(url_for('manage_pw'))

        if input_pw == "dbchange":
            session['allow_db_admin'] = True
            return redirect(url_for('db_admin'))

        conn = get_db(); c = conn.cursor()
        c.execute("SELECT password FROM auth WHERE id = 1")
        row = c.fetchone()
        conn.close()

        if row and input_pw == row[0]:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "パスワードが正しくありません。"
    return render_template("login.html", error=error)

@app.route("/manage_pw")
def manage_pw():
    if not session.get('allow_change'):
        return redirect(url_for('login'))
    return render_template("manage_pw.html")

@app.route("/update_password", methods=["POST"])
def update_password():
    if not session.get('allow_change'):
        return redirect(url_for('login'))

    new_pw = request.form.get("new_password", "").strip()
    if new_pw:
        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE auth SET password = ? WHERE id = 1", (new_pw,))
        conn.commit(); conn.close()
        session.pop('allow_change', None)

    return redirect(url_for('login'))

@app.route("/db_admin")
def db_admin():
    if not session.get('allow_db_admin'):
        return redirect(url_for('login'))

    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM employees"); emps = c.fetchall()
    c.execute("SELECT * FROM records"); recs = c.fetchall()
    c.execute("SELECT * FROM settings"); sets = c.fetchall()
    c.execute("SELECT * FROM auth"); auths = c.fetchall()
    conn.close()

    return render_template("db_admin.html", employees=emps, records=recs, settings=sets, auths=auths)

@app.route("/update_db_all/<table_name>/<int:id>", methods=["POST"])
def update_db_all(table_name, id):
    if not session.get('allow_db_admin'): return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()

    if table_name == "employees":
        c.execute("UPDATE employees SET name=? WHERE id=?", (request.form.get("name"), id))
    elif table_name == "records":
        c.execute("UPDATE records SET employee_id=?, date=?, start_time=?, end_time=?, minutes=? WHERE id=?",
                  (request.form.get("emp_id"), request.form.get("date"), request.form.get("start"), request.form.get("end"), request.form.get("mins"), id))
    elif table_name == "settings":
        c.execute("UPDATE settings SET common_wage=? WHERE id=?", (request.form.get("wage"), id))
    elif table_name == "auth":
        c.execute("UPDATE auth SET password=? WHERE id=?", (request.form.get("password"), id))

    conn.commit(); conn.close()
    return redirect(url_for('db_admin'))

@app.route("/delete_db_row/<table_name>/<int:id>", methods=["POST"])
def delete_db_row(table_name, id):
    if not session.get('allow_db_admin'):
        return redirect(url_for('login'))

    conn = get_db(); c = conn.cursor()
    if table_name in ["employees", "records", "settings", "auth"]:
        c.execute(f"DELETE FROM {table_name} WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('db_admin'))

@app.route("/delete_direct/<table_name>/<int:id>")
def delete_direct(table_name, id):
    if not session.get('allow_db_admin'): return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    if table_name in ["employees", "records"]:
        c.execute(f"DELETE FROM {table_name} WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('db_admin'))

@app.route("/update_all_bulk", methods=["POST"])
def update_all_bulk():
    if not session.get('allow_db_admin'): return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()

    try:
        emp_ids = request.form.getlist("emp_id_list")
        for eid in emp_ids:
            name = request.form.get(f"name_{eid}")
            if name:
                c.execute("UPDATE employees SET name = ? WHERE id = ?", (name, eid))

        rec_ids = request.form.getlist("rec_id_list")
        if rec_ids:
            c.execute("DELETE FROM records")
            for rid in rec_ids:
                emp_id = request.form.get(f"rec_emp_{rid}")
                date = request.form.get(f"rec_date_{rid}")
                start = request.form.get(f"rec_start_{rid}")
                end = request.form.get(f"rec_end_{rid}")
                mins = request.form.get(f"rec_mins_{rid}")
                c.execute("INSERT INTO records (id, employee_id, date, start_time, end_time, minutes) VALUES (?, ?, ?, ?, ?, ?)",
                          (rid, emp_id, date, start, end, mins))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"更新に失敗しました: {e}", 500
    finally:
        conn.close()

    return redirect(url_for('db_admin'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/", methods=["GET", "POST"])
def index():
    edit_id = request.args.get('edit_id')
    conn = get_db(); c = conn.cursor()
    if request.method == "POST":
        name, wage, tid = request.form.get("name"), request.form.get("wage"), request.form.get("target_id")
        if name:
            if tid: c.execute("UPDATE employees SET name=? WHERE id=?", (name, tid))
            else: c.execute("INSERT INTO employees (name) VALUES (?)", (name,))
        if wage: c.execute("UPDATE settings SET common_wage = ? WHERE id = 1", (int(wage),))
        conn.commit(); return redirect(url_for('index'))

    c.execute("SELECT * FROM employees"); employees = c.fetchall()
    c.execute("SELECT common_wage FROM settings WHERE id = 1"); wage = c.fetchone()[0]
    edit_name = None
    if edit_id:
        c.execute("SELECT name FROM employees WHERE id=?", (edit_id,))
        res = c.fetchone(); edit_name = res[0] if res else None
    conn.close()
    return render_template("index.html", employees=employees, wage=wage, edit_id=edit_id, edit_name=edit_name)

@app.route("/work/<int:eid>", methods=["GET", "POST"])
def work(eid):
    target_month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    edit_id = request.args.get('edit_id')
    conn = get_db(); c = conn.cursor()
    if request.method == "POST":
        rid, date, st, et = request.form.get("rid"), request.form["date"], request.form["start_time"], request.form["end_time"]
        try:
            t1, t2 = datetime.strptime(st, "%H:%M"), datetime.strptime(et, "%H:%M")
            m = int((t2 - t1).total_seconds() // 60)
            if m < 0: m += 1440
            if rid: c.execute("UPDATE records SET date=?, start_time=?, end_time=?, minutes=? WHERE id=?", (date, st, et, m, rid))
            else: c.execute("INSERT INTO records (employee_id, date, start_time, end_time, minutes) VALUES (?,?,?,?,?)", (eid, date, st, et, m))
            conn.commit()
        except: pass
        return redirect(url_for('work', eid=eid, month=target_month))
    c.execute("SELECT * FROM records WHERE employee_id=? AND date LIKE ? ORDER BY date DESC", (eid, f"{target_month}%"))
    raw_records = c.fetchall()
    formatted = []
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    for r in raw_records:
        r_l = list(r)
        try:
            d = datetime.strptime(r[2], '%Y-%m-%d')
            r_l[2] = d.strftime(f'%Y年%m月%d日({weekdays[d.weekday()]})')
        except: pass
        formatted.append(r_l)
    c.execute("SELECT name FROM employees WHERE id=?", (eid,))
    name = c.fetchone()[0]; conn.close()
    edit_data = next((r for r in raw_records if str(r[0]) == edit_id), None)
    return render_template("work.html", records=formatted, name=name, eid=eid, target_month=target_month, edit_data=edit_data)

@app.route("/summary")
def summary():
    target_month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT common_wage FROM settings WHERE id = 1"); wage = c.fetchone()[0]
    c.execute("SELECT e.name, IFNULL(SUM(r.minutes), 0) FROM employees e LEFT JOIN records r ON e.id = r.employee_id AND r.date LIKE ? GROUP BY e.id", (f"{target_month}%",))
    data = [(n, m, int(m * (wage / 60))) for n, m in c.fetchall()]; conn.close()
    return render_template("summary.html", data=data, target_month=target_month)

@app.route("/delete/<int:eid>", methods=["POST"])
def delete_employee(eid):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM records WHERE employee_id = ?", (eid,))
        c.execute("DELETE FROM employees WHERE id = ?", (eid,))
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route("/delete_all", methods=["POST"])
def delete_all():
    conn = get_db(); c = conn.cursor(); c.execute("DELETE FROM records"); c.execute("DELETE FROM employees"); conn.commit(); conn.close()
    return redirect(url_for('index'))

@app.route("/delete_record/<int:rid>/<int:eid>")
def delete_record(rid, eid):
    m = request.args.get('month'); conn = get_db(); c = conn.cursor(); c.execute("DELETE FROM records WHERE id=?", (rid,)); conn.commit(); conn.close()
    return redirect(url_for('work', eid=eid, month=m))

if __name__ == "__main__":
    app.run(debug=True)
