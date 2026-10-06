from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import ollama
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

app.secret_key = "memorymap-secret-key"


# ==========================================
# DATABASE
# ==========================================

DATABASE = "memorymap.db"


def get_db():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# CREATE DATABASE TABLES
# ==========================================

def init_db():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ==========================================
# SIGNUP
# ==========================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_db()

        try:

            connection.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, hashed_password)
            )

            connection.commit()
            connection.close()

            flash("Account created successfully! Please login.")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            connection.close()

            flash("Email already exists.")

            return redirect(url_for("signup"))

    return render_template("signup.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db()

    memories = connection.execute(
        """
        SELECT * FROM memories
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        memories=memories
    )


# ==========================================
# ADD MEMORY
# ==========================================

@app.route("/add-memory", methods=["POST"])
def add_memory():

    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form["title"]
    content = request.form["content"]
    category = request.form["category"]

    connection = get_db()

    connection.execute(
        """
        INSERT INTO memories
        (user_id, title, content, category)
        VALUES (?, ?, ?, ?)
        """,
        (
            session["user_id"],
            title,
            content,
            category
        )
    )

    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


# ==========================================
# DELETE MEMORY
# ==========================================

@app.route("/delete-memory/<int:memory_id>")
def delete_memory(memory_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db()

    connection.execute(
        """
        DELETE FROM memories
        WHERE id = ? AND user_id = ?
        """,
        (
            memory_id,
            session["user_id"]
        )
    )

    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


# ==========================================
# PROFILE
# ==========================================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db()

    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    connection.close()

    return render_template(
        "profile.html",
        user=user
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ==========================================
# AI PAGE
# ==========================================

@app.route("/ai", methods=["GET", "POST"])
def ai():

    if "user_id" not in session:
        return redirect(url_for("login"))

    answer = None
    topic = ""

    if request.method == "POST":

        topic = request.form.get("topic", "").strip()

        if topic:

            try:

                response = ollama.chat(
                    model="llama3.2",
                    messages=[
                        {
                            "role": "system",
                            "content": """
                            You are MemoryMap AI.

                            Answer the user's question clearly and accurately.

                            Explain difficult topics in simple language.

                            Use headings, bullet points, and examples
                            when useful.

                            The user may ask about:

                            - Programming
                            - Artificial Intelligence
                            - Machine Learning
                            - Computer Science
                            - College subjects
                            - General knowledge
                            """
                        },
                        {
                            "role": "user",
                            "content": topic
                        }
                    ]
                )

                answer = response["message"]["content"]

            except Exception as e:

                print("")
                print("==========================================")
                print("OLLAMA ERROR:")
                print(repr(e))
                print("==========================================")
                print("")

                answer = (
                    "AI could not generate a response.\n\n"
                    "Please check the terminal for the exact error."
                )

    return render_template(
        "ai.html",
        answer=answer,
        topic=topic
    )
# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)