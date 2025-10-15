import os
import pymysql
from flask import Flask, request, redirect, render_template_string, session
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecret")

# --- MySQL Configuration ---
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Root@1234")

root_config = {
    "host": MYSQL_HOST,
    "user": MYSQL_USER,
    "password": MYSQL_PASSWORD
}

# --- Utility functions ---
def get_root_connection():
    return pymysql.connect(**root_config, cursorclass=pymysql.cursors.DictCursor)

def init_db(db_name):
    conn = get_root_connection()
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cursor.execute(f"USE `{db_name}`")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_connection(db_name):
    return pymysql.connect(database=db_name, **root_config, cursorclass=pymysql.cursors.DictCursor)

def list_databases():
    conn = get_root_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES")
    dbs = [row['Database'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    exclude = {"information_schema", "mysql", "performance_schema", "sys"}
    return [db for db in dbs if db not in exclude]

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST" and "db_name" in request.form:
        db_name = request.form["db_name"].strip()
        if db_name:
            init_db(db_name)
            session["db_name"] = db_name
        return redirect("/")

    db_name = session.get("db_name")
    if not db_name:
        databases = list_databases()
        template = """
        <h2>Select / Create Database</h2>
        <form method="POST">
            Database name: <input type="text" name="db_name" required>
            <button type="submit">Use/Create DB</button>
        </form>

        <h2>Existing Databases</h2>
        <ul>
            {% for db in databases %}
                <li>
                    <form method="POST" style="display:inline;">
                        <input type="hidden" name="db_name" value="{{ db }}">
                        <button type="submit">{{ db }}</button>
                    </form>
                </li>
            {% endfor %}
        </ul>
        """
        return render_template_string(template, databases=databases)

    conn = get_connection(db_name)
    cursor = conn.cursor()

    if request.method == "POST" and "name" in request.form:
        name = request.form.get("name")
        email = request.form.get("email")
        if name and email:
            cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
            conn.commit()
        return redirect("/")

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Registration - {{ db_name }}</title>
    </head>
    <body>
        <h2>Active Database: {{ db_name }}</h2>
        <form method="POST">
            <input type="hidden" name="switch" value="1">
            <button type="submit" formaction="/switch_db">Switch Database</button>
        </form>

        <h2>Add User</h2>
        <form method="POST">
            Name: <input type="text" name="name" required><br><br>
            Email: <input type="email" name="email" required><br><br>
            <button type="submit">Add</button>
        </form>

        <h2>All Users in {{ db_name }}</h2>
        <table border="1" cellpadding="5">
            <tr><th>ID</th><th>Name</th><th>Email</th></tr>
            {% for user in users %}
                <tr>
                    <td>{{ user.id }}</td>
                    <td>{{ user.name }}</td>
                    <td>{{ user.email }}</td>
                </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(template, users=users, db_name=db_name)

@app.route("/switch_db", methods=["POST"])
def switch_db():
    session.pop("db_name", None)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=True)

