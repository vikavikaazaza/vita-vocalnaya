import csv
import io
import os
import sqlite3
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, Response, request, redirect, url_for, render_template_string

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "studio_bot.sqlite3")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "change-me")

app = Flask(__name__)

LOGIN_HTML = """
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ВИТА ВОКАЛЬНАЯ — вход</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Inter,Arial,sans-serif;background:#f6f3f7;color:#242127}
.login{max-width:420px;margin:10vh auto;padding:32px}
.box{background:#fff;border-radius:24px;padding:30px;box-shadow:0 10px 35px #00000012}
h1{margin:0 0 8px;font-size:28px}
p{color:#756d78}
input,button{width:100%;padding:14px;border-radius:12px;margin-top:12px;font-size:15px}
input{border:1px solid #ddd5df}
button{border:0;background:#242127;color:#fff;cursor:pointer}
.error{color:#b42318}
</style>
</head>
<body>
<div class="login">
<div class="box">
<h1>ВИТА ВОКАЛЬНАЯ</h1>
<p>Панель администратора</p>
<form method="post">
<input type="password" name="password" placeholder="Пароль" autofocus>
<button>Войти</button>
</form>
{% if error %}<p class="error">{{error}}</p>{% endif %}
</div>
</div>
</body>
</html>
"""

HTML = """
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ВИТА ВОКАЛЬНАЯ — дашборд</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Inter,Arial,sans-serif;background:#f6f3f7;color:#242127}
.container{max-width:1450px;margin:auto;padding:24px}
header{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:24px}
.brand h1{margin:0;font-size:28px}.brand p{margin:5px 0 0;color:#817984}
nav{display:flex;flex-wrap:wrap;gap:8px}
nav a,.btn{display:inline-block;text-decoration:none;color:#302b32;background:#fff;border:1px solid #e6e0e8;border-radius:10px;padding:9px 12px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.card{background:#fff;border-radius:18px;padding:18px;box-shadow:0 5px 20px #00000009}
.card .label{color:#756d78;font-size:13px}.big{font-size:32px;font-weight:800;margin-top:8px}
.section{margin-top:22px}.section h2{font-size:20px;margin:0 0 12px}
.chartgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.chartbox{height:310px}.chartbox canvas{width:100%!important;height:100%!important}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:16px;overflow:hidden}
th,td{text-align:left;padding:11px 12px;border-bottom:1px solid #eee7ef;font-size:13px;vertical-align:top}
th{font-size:12px;color:#766d78;background:#fbf9fb}
.badge{display:inline-block;padding:5px 8px;border-radius:999px;background:#f0ebf2;font-size:12px}
.badge.new{background:#fff2cc}.badge.work{background:#e7f0ff}.badge.done{background:#e5f6ea}.badge.cancel{background:#fbe5e5}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.filters input,.filters select{padding:10px;border:1px solid #ddd5df;border-radius:10px;background:#fff}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.muted{color:#827985}.small{font-size:12px;color:#827985}
.progress{height:8px;background:#eee9ef;border-radius:99px;overflow:hidden;margin-top:7px}
.progress span{display:block;height:100%;background:#7c687e}
.statrow{display:flex;justify-content:space-between;margin-top:10px}
.actions{display:flex;gap:8px;flex-wrap:wrap}
@media(max-width:1000px){.grid{grid-template-columns:repeat(2,1fr)}.chartgrid,.two{grid-template-columns:1fr}}
@media(max-width:600px){.container{padding:14px}.grid{grid-template-columns:1fr}.big{font-size:27px}header{align-items:flex-start;flex-direction:column}table{display:block;overflow-x:auto;white-space:nowrap}}
</style>
</head>
<body>
<div class="container">

<header>
<div class="brand">
<h1>ВИТА ВОКАЛЬНАЯ</h1>
<p>Административная панель · обновлено {{ now }}</p>
</div>
<nav>
<a href="/?token={{token}}">Главная</a>
<a href="/users?token={{token}}">Пользователи</a>
<a href="/applications?token={{token}}">Заявки</a>
<a href="/analytics?token={{token}}">Аналитика</a>
<a href="/export/users.csv?token={{token}}">⬇ Пользователи</a>
<a href="/export/applications.csv?token={{token}}">⬇ Заявки</a>
</nav>
</header>

<div class="grid">
<div class="card"><div class="label">Всего пользователей</div><div class="big">{{stats.total}}</div></div>
<div class="card"><div class="label">Активны за 24 часа</div><div class="big">{{stats.d1}}</div></div>
<div class="card"><div class="label">Новых за 7 дней</div><div class="big">{{stats.new7}}</div></div>
<div class="card"><div class="label">Новых за 30 дней</div><div class="big">{{stats.new30}}</div></div>
<div class="card"><div class="label">Заявок всего</div><div class="big">{{stats.apps}}</div></div>
<div class="card"><div class="label">Заявок сегодня</div><div class="big">{{stats.apps_today}}</div></div>
<div class="card"><div class="label">Конверсия в заявку</div><div class="big">{{stats.conversion}}%</div></div>
<div class="card"><div class="label">Заблокировали бота</div><div class="big">{{stats.blocked}}</div></div>
</div>

<div class="section chartgrid">
<div class="card chartbox"><h2>Пользователи по дням</h2><canvas id="usersChart"></canvas></div>
<div class="card chartbox"><h2>Заявки по дням</h2><canvas id="appsChart"></canvas></div>
</div>

<div class="section two">
<div class="card">
<h2>Воронка</h2>
<div class="statrow"><span>Пользователи</span><b>{{stats.total}}</b></div>
<div class="progress"><span style="width:100%"></span></div>
<div class="statrow"><span>Оставили заявку</span><b>{{stats.apps}}</b></div>
<div class="progress"><span style="width:{{funnel_pct}}%"></span></div>
<p class="small">Конверсия считается как заявки / количество пользователей.</p>
</div>

<div class="card">
<h2>Заявки по типу</h2>
<div class="statrow"><span>Вокал</span><b>{{stats.booking_apps}}</b></div>
<div class="progress"><span style="width:{{booking_pct}}%"></span></div>
<div class="statrow"><span>Аренда</span><b>{{stats.rent_apps}}</b></div>
<div class="progress"><span style="width:{{rent_pct}}%"></span></div>
</div>
</div>

<div class="section">
<h2>Последние заявки</h2>
<table>
<tr><th>Дата</th><th>Тип</th><th>Имя</th><th>TG</th><th>Телефон</th><th>Преподаватель</th><th>Уровень</th><th>Дни</th><th>Время</th></tr>
{% for r in applications %}
<tr>
<td>{{r.created_at}}</td>
<td><span class="badge">{{r.app_type}}</span></td>
<td>{{r.name}}</td>
<td>{{r.username or '—'}}</td>
<td>{{r.phone or '—'}}</td>
<td>{{r.teacher or 'не выбран'}}</td>
<td>{{r.level or '—'}}</td>
<td>{{r.days or '—'}}</td>
<td>{{r.time or '—'}}</td>
</tr>
{% endfor %}
</table>
</div>

<div class="section">
<h2>Последние пользователи</h2>
<table>
<tr><th>ID</th><th>Username</th><th>Имя</th><th>Телефон</th><th>Создан</th><th>Последняя активность</th><th>Действий</th><th>Статус</th></tr>
{% for r in users %}
<tr>
<td>{{r[0]}}</td><td>{{r[1] or '—'}}</td><td>{{r[2] or '—'}} {{r[3] or ''}}</td><td>{{r[4] or '—'}}</td>
<td>{{r[5]}}</td><td>{{r[6]}}</td><td>{{r[7]}}</td><td>{{'Заблокировал' if r[8] else 'Активен'}}</td>
</tr>
{% endfor %}
</table>
</div>

<div class="section">
<h2>Последняя активность</h2>
<table>
<tr><th>Дата</th><th>Telegram ID</th><th>Действие</th></tr>
{% for r in activities %}
<tr><td>{{r[2]}}</td><td>{{r[0]}}</td><td>{{r[1]}}</td></tr>
{% endfor %}
</table>
</div>

</div>

<script>
const labels={{chart_labels|safe}};
new Chart(document.getElementById('usersChart'),{
type:'line',
data:{labels:labels,datasets:[{label:'Новые пользователи',data:{{users_daily|safe}},tension:.3}]},
options:{responsive:true,maintainAspectRatio:false}
});
new Chart(document.getElementById('appsChart'),{
type:'bar',
data:{labels:labels,datasets:[{label:'Заявки',data:{{apps_daily|safe}}}]},
options:{responsive:true,maintainAspectRatio:false}
});
</script>
</body>
</html>
"""

USERS_HTML = """
<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Пользователи</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f6f3f7;font-family:Arial;color:#242127}.container{max-width:1450px;margin:auto;padding:24px}
nav{margin-bottom:20px}nav a{background:#fff;padding:9px 12px;border-radius:10px;text-decoration:none;color:#333;border:1px solid #e5dfe7}
.card{background:#fff;border-radius:18px;padding:18px;box-shadow:0 5px 20px #00000009}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}.filters input{padding:11px;border:1px solid #ddd5df;border-radius:10px;min-width:240px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:11px;border-bottom:1px solid #eee;font-size:13px}th{color:#766d78;font-size:12px}
@media(max-width:700px){table{display:block;overflow-x:auto;white-space:nowrap}.container{padding:14px}}
</style></head><body><div class="container">
<nav><a href="/?token={{token}}">← Главная</a></nav>
<div class="card"><h1>Пользователи</h1>
<form class="filters"><input name="q" value="{{q}}" placeholder="Поиск по имени, username или ID"><input type="hidden" name="token" value="{{token}}"><button>Найти</button></form>
<table><tr><th>ID</th><th>Username</th><th>Имя</th><th>Телефон</th><th>Создан</th><th>Последняя активность</th><th>Действий</th><th>Статус</th></tr>
{% for r in users %}<tr><td>{{r[0]}}</td><td>{{r[1] or '—'}}</td><td>{{r[2] or '—'}} {{r[3] or ''}}</td><td>{{r[4] or '—'}}</td><td>{{r[5]}}</td><td>{{r[6]}}</td><td>{{r[7]}}</td><td>{{'Заблокировал' if r[8] else 'Активен'}}</td></tr>{% endfor %}
</table></div></div></body></html>
"""

APPLICATIONS_HTML = """
<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Заявки</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f3f7;font-family:Arial;color:#242127}.container{max-width:1450px;margin:auto;padding:24px}
nav{margin-bottom:20px}nav a{background:#fff;padding:9px 12px;border-radius:10px;text-decoration:none;color:#333;border:1px solid #e5dfe7}
.card{background:#fff;border-radius:18px;padding:18px;box-shadow:0 5px 20px #00000009}.filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
select{padding:10px;border:1px solid #ddd5df;border-radius:10px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:11px;border-bottom:1px solid #eee;font-size:13px;vertical-align:top}th{color:#766d78;font-size:12px}
.badge{padding:5px 8px;border-radius:999px;background:#f0ebf2}
@media(max-width:700px){table{display:block;overflow-x:auto;white-space:nowrap}.container{padding:14px}}
</style></head><body><div class="container">
<nav><a href="/?token={{token}}">← Главная</a></nav>
<div class="card"><h1>Заявки</h1>
<form class="filters"><input type="hidden" name="token" value="{{token}}"><select name="type"><option value="">Все типы</option><option value="booking" {% if type=='booking' %}selected{% endif %}>🎤 Вокал</option><option value="rent" {% if type=='rent' %}selected{% endif %}>🏠 Аренда</option></select><button>Применить</button></form>
<table><tr><th>Дата</th><th>Тип</th><th>Имя</th><th>TG</th><th>Телефон</th><th>Преподаватель</th><th>Уровень</th><th>Дни</th><th>Время</th></tr>
{% for r in applications %}<tr><td>{{r[7]}}</td><td><span class="badge">{{'🎤 Вокал' if r[8]=='booking' else '🏠 Аренда'}}</span></td><td>{{r[0]}}</td><td>{{r[1] or '—'}}</td><td>{{r[2] or '—'}}</td><td>{{r[3] or '—'}}</td><td>{{r[4] or '—'}}</td><td>{{r[6] or '—'}}</td><td>{{r[5] or '—'}}</td></tr>{% endfor %}
</table></div></div></body></html>
"""

ANALYTICS_HTML = """
<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Аналитика</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>*{box-sizing:border-box}body{margin:0;background:#f6f3f7;font-family:Arial;color:#242127}.container{max-width:1200px;margin:auto;padding:24px}nav{margin-bottom:20px}nav a{background:#fff;padding:9px 12px;border-radius:10px;text-decoration:none;color:#333;border:1px solid #e5dfe7}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.card{background:#fff;border-radius:18px;padding:18px}.chart{height:360px}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style></head><body><div class="container">
<nav><a href="/?token={{token}}">← Главная</a></nav><h1>Аналитика</h1>
<div class="grid">
<div class="card chart"><h2>Уровень вокала</h2><canvas id="levels"></canvas></div>
<div class="card chart"><h2>Преподаватели</h2><canvas id="teachers"></canvas></div>
<div class="card chart"><h2>Активность по действиям</h2><canvas id="actions"></canvas></div>
<div class="card"><h2>Аренда — цели</h2>{% for k,v in rent_purposes %}<p>{{k}} <b style="float:right">{{v}}</b></p>{% endfor %}</div>
</div></div>
<script>
new Chart(document.getElementById('levels'),{type:'doughnut',data:{labels:{{level_labels|safe}},datasets:[{data:{{level_values|safe}}}]},options:{responsive:true,maintainAspectRatio:false}});
new Chart(document.getElementById('teachers'),{type:'bar',data:{labels:{{teacher_labels|safe}},datasets:[{label:'Заявки',data:{{teacher_values|safe}}}]},options:{responsive:true,maintainAspectRatio:false}});
new Chart(document.getElementById('actions'),{type:'bar',data:{labels:{{action_labels|safe}},datasets:[{label:'Действия',data:{{action_values|safe}}}]},options:{responsive:true,maintainAspectRatio:false}});
</script></body></html>
"""

def conn():
    return sqlite3.connect(DB_PATH)

def authorized():
    return request.args.get("token") == DASHBOARD_PASSWORD

def q1(db, sql, params=()):
    return db.execute(sql, params).fetchone()[0]

def daily_counts(db, table, date_col, days=14):
    result = []
    today = datetime.now().date()
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        start = datetime.combine(day, datetime.min.time()).isoformat()
        end = datetime.combine(day + timedelta(days=1), datetime.min.time()).isoformat()
        result.append(q1(db, f"SELECT COUNT(*) FROM {table} WHERE {date_col}>=? AND {date_col}<?", (start, end)))
    labels = [(today - timedelta(days=i)).strftime("%d.%m") for i in range(days - 1, -1, -1)]
    return labels, result

def applications_data(db, limit=100, app_type=None):
    sql = """SELECT name, username, phone, teacher, level, time, days, created_at
             FROM applications"""
    params = []
    if app_type == "booking":
        # The existing schema has no application type column, so booking/rent is inferred
        # from fields: rent applications have purpose/datetime_text in the current bot schema.
        sql = """SELECT name, username, phone, teacher, level, time, days, created_at,
                        CASE WHEN teacher IS NULL OR teacher='' THEN 'rent' ELSE 'booking' END
                 FROM applications"""
    else:
        sql = """SELECT name, username, phone, teacher, level, time, days, created_at,
                        CASE WHEN teacher IS NULL OR teacher='' THEN 'rent' ELSE 'booking' END
                 FROM applications"""
    if app_type in ("booking", "rent"):
        sql += " WHERE " + ("(teacher IS NOT NULL AND teacher!='')" if app_type == "booking" else "(teacher IS NULL OR teacher='')")
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return db.execute(sql, params).fetchall()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            return redirect(url_for("index", token=DASHBOARD_PASSWORD))
        return render_template_string(LOGIN_HTML, error="Неверный пароль")

    if not authorized():
        return render_template_string(LOGIN_HTML, error=None)

    now = datetime.now()
    d1 = (now - timedelta(days=1)).isoformat()
    d7 = (now - timedelta(days=7)).isoformat()
    d30 = (now - timedelta(days=30)).isoformat()
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    with conn() as db:
        total = q1(db, "SELECT COUNT(*) FROM users")
        apps = q1(db, "SELECT COUNT(*) FROM applications")
        stats = {
            "total": total,
            "d1": q1(db, "SELECT COUNT(*) FROM users WHERE last_activity>=?", (d1,)),
            "new7": q1(db, "SELECT COUNT(*) FROM users WHERE created_at>=?", (d7,)),
            "new30": q1(db, "SELECT COUNT(*) FROM users WHERE created_at>=?", (d30,)),
            "apps": apps,
            "apps_today": q1(db, "SELECT COUNT(*) FROM applications WHERE created_at>=?", (start_day,)),
            "blocked": q1(db, "SELECT COUNT(*) FROM users WHERE is_blocked=1"),
            "conversion": round((apps / total) * 100, 1) if total else 0,
            "booking_apps": q1(db, "SELECT COUNT(*) FROM applications WHERE teacher IS NOT NULL AND teacher!=''"),
            "rent_apps": q1(db, "SELECT COUNT(*) FROM applications WHERE teacher IS NULL OR teacher=''"),
        }
        stats["actions"] = q1(db, "SELECT COUNT(*) FROM activities")

        users = db.execute("""
            SELECT telegram_id, username, first_name, last_name, phone,
                   created_at, last_activity, activity_count, is_blocked
            FROM users ORDER BY last_activity DESC LIMIT 100
        """).fetchall()

        activities = db.execute("""
            SELECT telegram_id, action, created_at
            FROM activities ORDER BY id DESC LIMIT 150
        """).fetchall()

        applications = applications_data(db, 100)
        labels, users_daily = daily_counts(db, "users", "created_at", 14)
        _, apps_daily = daily_counts(db, "applications", "created_at", 14)

    total_apps = stats["booking_apps"] + stats["rent_apps"]
    booking_pct = round(stats["booking_apps"] / total_apps * 100) if total_apps else 0
    rent_pct = round(stats["rent_apps"] / total_apps * 100) if total_apps else 0
    funnel_pct = min(100, round(stats["apps"] / stats["total"] * 100, 1)) if stats["total"] else 0

    return render_template_string(
        HTML,
        stats=stats,
        users=users,
        activities=activities,
        applications=[
            type("R", (), dict(
                name=r[0], username=r[1], phone=r[2], teacher=r[3], level=r[4],
                time=r[5], days=r[6], created_at=r[7],
                app_type="🎤 Вокал" if r[8] == "booking" else "🏠 Аренда"
            )) for r in applications
        ],
        chart_labels=labels,
        users_daily=users_daily,
        apps_daily=apps_daily,
        booking_pct=booking_pct,
        rent_pct=rent_pct,
        funnel_pct=funnel_pct,
        now=now.strftime("%d.%m.%Y %H:%M"),
        token=DASHBOARD_PASSWORD
    )

@app.route("/users")
def users_page():
    if not authorized():
        return render_template_string(LOGIN_HTML, error=None)
    q = request.args.get("q", "").strip()
    with conn() as db:
        if q:
            like = f"%{q}%"
            users = db.execute("""
                SELECT telegram_id, username, first_name, last_name, phone,
                       created_at, last_activity, activity_count, is_blocked
                FROM users
                WHERE CAST(telegram_id AS TEXT) LIKE ?
                   OR username LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                ORDER BY last_activity DESC LIMIT 500
            """, (like, like, like, like)).fetchall()
        else:
            users = db.execute("""
                SELECT telegram_id, username, first_name, last_name, phone,
                       created_at, last_activity, activity_count, is_blocked
                FROM users ORDER BY last_activity DESC LIMIT 500
            """).fetchall()
    return render_template_string(USERS_HTML, users=users, q=q, token=DASHBOARD_PASSWORD)

@app.route("/applications")
def applications_page():
    if not authorized():
        return render_template_string(LOGIN_HTML, error=None)
    app_type = request.args.get("type", "")
    with conn() as db:
        applications = applications_data(db, 500, app_type if app_type in ("booking", "rent") else None)
    return render_template_string(APPLICATIONS_HTML, applications=applications, type=app_type, token=DASHBOARD_PASSWORD)

@app.route("/analytics")
def analytics():
    if not authorized():
        return render_template_string(LOGIN_HTML, error=None)

    with conn() as db:
        levels = db.execute("""
            SELECT COALESCE(level,'Не указано'), COUNT(*)
            FROM applications
            WHERE teacher IS NOT NULL AND teacher!=''
            GROUP BY level ORDER BY COUNT(*) DESC
        """).fetchall()
        teachers = db.execute("""
            SELECT COALESCE(teacher,'Не указан'), COUNT(*)
            FROM applications
            WHERE teacher IS NOT NULL AND teacher!=''
            GROUP BY teacher ORDER BY COUNT(*) DESC
        """).fetchall()
        actions = db.execute("""
            SELECT action, COUNT(*) FROM activities
            GROUP BY action ORDER BY COUNT(*) DESC LIMIT 20
        """).fetchall()

    # The current bot schema does not store rent purpose separately.
    rent_purposes = [("Цель аренды пока не хранится в таблице applications", "—")]

    return render_template_string(
        ANALYTICS_HTML,
        token=DASHBOARD_PASSWORD,
        level_labels=[x[0] for x in levels],
        level_values=[x[1] for x in levels],
        teacher_labels=[x[0] for x in teachers],
        teacher_values=[x[1] for x in teachers],
        action_labels=[x[0] for x in actions],
        action_values=[x[1] for x in actions],
        rent_purposes=rent_purposes
    )

def export_table(table, columns, token):
    if token != DASHBOARD_PASSWORD:
        return Response("Forbidden", status=403)
    with conn() as db:
        rows = db.execute(f"SELECT {columns} FROM {table}").fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(columns.split(","))
    writer.writerows(rows)
    return Response(
        out.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={table}.csv"}
    )

@app.route("/export/users.csv")
def users_csv():
    return export_table(
        "users",
        "telegram_id,username,first_name,last_name,phone,created_at,last_activity,activity_count,is_blocked",
        request.args.get("token")
    )

@app.route("/export/activities.csv")
def activities_csv():
    return export_table(
        "activities",
        "id,telegram_id,action,created_at",
        request.args.get("token")
    )

@app.route("/export/applications.csv")
def applications_csv():
    return export_table(
        "applications",
        "id,telegram_id,username,name,phone,teacher,level,time,days,created_at",
        request.args.get("token")
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
