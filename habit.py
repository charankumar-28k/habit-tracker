# STEP-BY-STEP YEARLY HABIT TRACKER (FLASK)
# STEP 1: Basic Flask App with Saved Data

from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3
from datetime import date
from datetime import date, timedelta
import random

app = Flask(__name__)
DB = "habits.db"

# ---------------- STEP 1: DATABASE SETUP ----------------
def init_db():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            habit_id INTEGER,
            day TEXT,
            value INTEGER,
            PRIMARY KEY (habit_id, day)
        )""")
        con.commit()

init_db()

# ---------------- STEP 2: FETCH HABITS ----------------
def get_habits():
    with sqlite3.connect(DB) as con:
        return con.execute("SELECT * FROM habits").fetchall()


def get_today_logs(today):
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT habit_id, value FROM logs WHERE day=?",
            (today,)
        ).fetchall()
    return {r[0]: r[1] for r in rows}

from datetime import timedelta

def get_week_logs():
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT habit_id, day, value FROM logs"
        ).fetchall()
    return {(r[0], r[1]): r[2] for r in rows}



def get_month_stats(year_month):
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            """
            SELECT COUNT(*) 
            FROM logs 
            WHERE value=1 AND substr(day,1,7)=?
            """,
            (year_month,)
        ).fetchone()
    return rows[0] if rows else 0


def get_year_logs(year):
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            """
            SELECT day, SUM(value) 
            FROM logs 
            WHERE substr(day,1,4)=?
            GROUP BY day
            """,
            (year,)
        ).fetchall()
    return {r[0]: r[1] for r in rows}




# ---------------- STEP 3: MAIN PAGE ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    from datetime import timedelta

    # --- Step 0: Define today first ---
    today = date.today().isoformat()

    # --- Handle GET parameter for week view ---
    start_day = request.args.get("day", today)

    # --- Helper function to get 7-day week ---
    def get_week_dates(start_date):
        start = date.fromisoformat(start_date)
        return [(start + timedelta(days=i)).isoformat() for i in range(7)]

    week = get_week_dates(start_day)

    # --- Handle POST (checkbox submit) ---
    if request.method == "POST":
        habit_id = request.form["habit_id"]
        value = 1 if request.form.get("value") else 0
        day = request.form.get("day", today)  # fallback to today

        with sqlite3.connect(DB) as con:
            con.execute(
                "REPLACE INTO logs (habit_id, day, value) VALUES (?, ?, ?)",
                (habit_id, day, value)
            )
            con.commit()
        return redirect(url_for("index"))

    # --- Prepare yearly heatmap data ---
    year = today[:4]
    year_logs = get_year_logs(year)

    days = []
    start = date(int(year), 1, 1)
    for i in range(365):
        d = start + timedelta(days=i)
        ds = d.isoformat()
        count = year_logs.get(ds, 0)

        if count == 0:
            level = 0
        elif count == 1:
            level = 1
        elif count == 2:
            level = 2
        else:
            level = 3

        days.append({
            "date": ds,
            "level": level
        })

    # --- Monthly stats ---
    year_month = today[:7]
    habits = get_habits()
    completed_month = get_month_stats(year_month)
    total_possible = len(habits) * 30

    # --- Weekly logs ---
    logs = get_week_logs()

    # --- Render template ---
    return render_template_string(
        TEMPLATE,
        days=days,
        completed_month=completed_month,
        total_possible=total_possible,
        habits=habits,
        logs=logs,
        week=week,
        today=today,
        start_day=start_day
    )


# ---------------- STEP 4: ADD HABIT ----------------
@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    with sqlite3.connect(DB) as con:
        con.execute("INSERT INTO habits (name) VALUES (?)", (name,))
        con.commit()
    return redirect(url_for("index"))

# ---------------- STEP 5: UI (MOBILE FRIENDLY) ----------------
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>


    <title>Habit Tracker</title>
    <style>
/* ---------- GLOBAL ---------- */
body {
    font-family: Arial, sans-serif;
    background: #f4f6f8;
    padding: 10px;
    margin: 0;
}

h1 {
    text-align: center;
}

button {
    padding: 10px;
    width: 100%;
    margin-top: 5px;
}

input {
    width: 100%;
    padding: 10px;
    margin-bottom: 5px;
}

/* ---------- CARD ---------- */
.card {
    background: white;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
}

/* ---------- YEARLY GRID ---------- */
.year-grid {
    display: grid;
    grid-template-columns: repeat(53, 14px); /* 53 weeks */
    gap: 3px;
}


.day {
    width: 16px;
    height: 16px;
    background: #ebedf0;
    border-radius: 3px;
}

/* GitHub-style levels */
.level-1 { background: #c6e48b; }
.level-2 { background: #7bc96f; }
.level-3 { background: #239a3b; }

    </style>
</head>
<body>
    <h1>📅 Daily Habit Tracker</h1>

    
<div class="year-grid">
    {% for d in days %}
        <div class="day level-{{ d.level }}" title="{{ d.date }}"></div>
    {% endfor %}
</div>




    

<div class="card">
    <h3>📊 Monthly Progress</h3>
    <p>Completed: {{ completed_month }} / {{ total_possible }}</p>
    <canvas id="monthChart"></canvas>
</div>



    <div class="card">
    <form method="get">
        <input type="date" name="day" value="{{start_day}}">
        <button>Load Week</button>
    </form>
    <div class="card">
    <h3>Add New Habit</h3>
    <form method="post" action="/add">
        <input type="text" name="name" placeholder="Habit name" required>
        <button type="submit">Add Habit</button>
    </form>
</div>

</div>

<div class="card">
    <table border="1" width="100%">
        <tr>
            <th>Habit</th>
            {% for d in week %}
                <th>{{ d[5:] }}</th>
            {% endfor %}
        </tr>

        {% for h in habits %}
        <tr>
            <td>{{ h[1] }}</td>
            {% for d in week %}
            <td align="center">
                <form method="post">
                    <input type="hidden" name="habit_id" value="{{h[0]}}">
                    <input type="hidden" name="day" value="{{d}}">
                    <input type="checkbox" name="value"
                    {% if logs.get((h[0], d)) == 1 %}checked{% endif %}
                    onchange="this.form.submit()">
                </form>
            </td>
            {% endfor %}
        </tr>
        {% endfor %}
    </table>
</div>


    <div class="card">
        <h3>{{today}}</h3>
        {% for h in habits %}
        <form method="post">
            <input type="hidden" name="habit_id" value="{{h[0]}}">
            <label>
                <input type="checkbox" name="value"{% if logs.get(h[0]) == 1 %}checked{% endif %}onchange="this.form.submit()"> {{h[1]}}

            </label>
        </form>
        {% endfor %}
    </div>



<script>
const ctx = document.getElementById('monthChart');

new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['Completed', 'Remaining'],
        datasets: [{
            data: [
                {{ completed_month }},
                {{ total_possible - completed_month }}
            ]
        }]
    }
});
</script>




</body>
</html>
"""

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

