import os
import socket

import pymysql
from flask import Flask, request, redirect, jsonify

app = Flask(__name__)


def get_db():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "admin"),
        password=os.environ.get("DB_PASSWORD", "password"),
        database=os.environ.get("DB_NAME", "statusdashboard"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


def init_db():
    try:
        conn = get_db()

        with conn.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS status_updates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    team_name VARCHAR(100) NOT NULL,
                    project VARCHAR(200) NOT NULL,
                    status ENUM(
                        'on_track',
                        'at_risk',
                        'blocked',
                        'completed'
                    ) DEFAULT 'on_track',
                    message TEXT NOT NULL,
                    author VARCHAR(100) NOT NULL,
                    instance_id VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS milestones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project VARCHAR(200) NOT NULL,
                    title VARCHAR(300) NOT NULL,
                    due_date DATE NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"DB init error: {e}")


@app.route("/health")
def health():
    try:
        conn = get_db()
        conn.cursor().execute("SELECT 1")
        conn.close()

        return jsonify({
            "status": "healthy",
            "instance": socket.gethostname()
        }), 200

    except Exception:
        return jsonify({
            "status": "unhealthy"
        }), 500


@app.route("/")
def dashboard():

    conn = get_db()

    with conn.cursor() as c:

        c.execute(
            "SELECT * FROM status_updates "
            "ORDER BY created_at DESC LIMIT 20"
        )

        updates = c.fetchall()

        c.execute(
            "SELECT status, COUNT(*) AS count "
            "FROM status_updates GROUP BY status"
        )

        counts = {
            row["status"]: row["count"]
            for row in c.fetchall()
        }

        c.execute(
            "SELECT COUNT(DISTINCT team_name) AS count "
            "FROM status_updates"
        )

        teams = c.fetchone()["count"]

    conn.close()

    html = f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>Team Status Dashboard</title>

        <style>

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: sans-serif;
            background: #0f172a;
            color: #f1f5f9;
            padding: 20px;
        }}

        h1 {{
            margin-bottom: 20px;
        }}

        .stats {{
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
        }}

        .stat {{
            background: #1e293b;
            padding: 16px 24px;
            border-radius: 8px;
            text-align: center;
        }}

        .stat b {{
            font-size: 1.5rem;
            display: block;
        }}

        .update {{
            background: #1e293b;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
        }}

        a {{
            color: #818cf8;
        }}

        </style>

    </head>

    <body>

        <h1>📋 Team Status Dashboard</h1>

        <p style="color:#64748b;margin-bottom:20px">
            Served by: {socket.gethostname()}
        </p>

        <div class="stats">

            <div class="stat">
                <b style="color:#10b981">
                    {counts.get("on_track", 0)}
                </b>
                On Track
            </div>

            <div class="stat">
                <b style="color:#f59e0b">
                    {counts.get("at_risk", 0)}
                </b>
                At Risk
            </div>

            <div class="stat">
                <b style="color:#ef4444">
                    {counts.get("blocked", 0)}
                </b>
                Blocked
            </div>

            <div class="stat">
                <b style="color:#3b82f6">
                    {teams}
                </b>
                Teams
            </div>

        </div>

        <p>
            <a href="/update">+ Post Update</a>
        </p>

        <br>
    """

    for update in updates:

        html += f"""
        <div class="update">

            <b>{update["team_name"]}</b> /
            {update["project"]} —

            <em>{update["status"]}</em>

            <br>

            {update["message"]}

            <br>

            <small style="color:#475569">
                by {update["author"]} · {update["created_at"]}
            </small>

        </div>
        """

    html += "</body></html>"

    return html


@app.route("/update", methods=["GET", "POST"])
def update():

    if request.method == "POST":

        conn = get_db()

        with conn.cursor() as c:

            c.execute(
                """
                INSERT INTO status_updates
                (
                    team_name,
                    project,
                    status,
                    message,
                    author,
                    instance_id
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    request.form["team_name"],
                    request.form["project"],
                    request.form["status"],
                    request.form["message"],
                    request.form["author"],
                    socket.gethostname()
                )
            )

        conn.commit()
        conn.close()

        return redirect("/")

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>Post Update</title>

        <style>

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: sans-serif;
            background: #0f172a;
            color: #f1f5f9;
            padding: 40px;
            max-width: 500px;
            margin: 0 auto;
        }

        h1 {
            margin-bottom: 20px;
        }

        input,
        select,
        textarea {
            width: 100%;
            padding: 10px;
            margin-bottom: 14px;
            border: 1px solid #334155;
            border-radius: 6px;
            background: #1e293b;
            color: #f1f5f9;
            font-size: 14px;
        }

        button {
            background: #6366f1;
            color: #fff;
            padding: 10px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }

        a {
            color: #818cf8;
        }

        </style>

    </head>

    <body>

        <h1>Post Update</h1>

        <form method="POST">

            <input
                name="team_name"
                placeholder="Team Name"
                required
            >

            <input
                name="project"
                placeholder="Project"
                required
            >

            <select name="status">

                <option value="on_track">
                    On Track
                </option>

                <option value="at_risk">
                    At Risk
                </option>

                <option value="blocked">
                    Blocked
                </option>

                <option value="completed">
                    Completed
                </option>

            </select>

            <textarea
                name="message"
                placeholder="Update message"
                required
            ></textarea>

            <input
                name="author"
                placeholder="Your Name"
                required
            >

            <button type="submit">
                Post Update
            </button>

            <a href="/">
                Cancel
            </a>

        </form>

    </body>

    </html>
    """


if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=80
    )
