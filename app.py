
import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "portal.db"

UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-key")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "doc", "docx",
    "txt", "csv", "xlsx", "pptx"
}


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)


# ---------------- HELPERS ----------------

def current_user_id():
    return session.get("user_id")


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user_id():
            return jsonify({"error": "Please login first"}), 401
        return func(*args, **kwargs)
    return wrapper


def notify(user_id, message):
    with get_db() as db:
        db.execute(
            "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
            (user_id, message)
        )


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def row_to_dict(row):
    return dict(row) if row else None


# ---------------- PAGE ROUTES ----------------

@app.route("/")
def home():
    if current_user_id():
        return render_template("index.html")
    return render_template("login.html")


@app.route("/login")
def login_page():
    if current_user_id():
        return render_template("index.html")
    return render_template("login.html")


@app.route("/signup")
def signup_page():
    if current_user_id():
        return render_template("index.html")
    return render_template("signup.html")


# ---------------- AUTH ----------------

@app.post("/api/signup")
def signup():
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    hashed_password = generate_password_hash(password)

    try:
        with get_db() as db:
            cursor = db.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password)
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email is already registered"}), 409

    session.clear()
    session["user_id"] = user_id

    return jsonify({"message": "Account created successfully"}), 201


@app.post("/api/login")
def login():
    data = request.get_json() or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session.clear()
    session["user_id"] = user["id"]

    return jsonify({"message": "Login successful"})


@app.post("/api/logout")
@login_required
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@app.get("/api/me")
@login_required
def get_profile():
    with get_db() as db:
        user = db.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (current_user_id(),)
        ).fetchone()

    return jsonify(row_to_dict(user))


@app.put("/api/me")
@login_required
def update_profile():
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    try:
        with get_db() as db:
            db.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (name, email, current_user_id())
            )
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email is already in use"}), 409

    return jsonify({"message": "Profile updated"})


# ---------------- DASHBOARD ----------------

@app.get("/api/dashboard")
@login_required
def dashboard():
    uid = current_user_id()

    with get_db() as db:
        total_projects = db.execute(
            "SELECT COUNT(*) FROM projects WHERE user_id = ?", (uid,)
        ).fetchone()[0]

        completed_projects = db.execute(
            "SELECT COUNT(*) FROM projects WHERE user_id = ? AND completed = 1",
            (uid,)
        ).fetchone()[0]

        pending_tasks = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 0",
            (uid,)
        ).fetchone()[0]

        total_tasks = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ?", (uid,)
        ).fetchone()[0]

    return jsonify({
        "total_projects": total_projects,
        "completed_projects": completed_projects,
        "pending_tasks": pending_tasks,
        "total_tasks": total_tasks
    })


# ---------------- PROJECTS ----------------

@app.get("/api/projects")
@login_required
def get_projects():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY id DESC",
            (current_user_id(),)
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.post("/api/projects")
@login_required
def create_project():
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Project name is required"}), 400

    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO projects (user_id, name) VALUES (?, ?)",
            (current_user_id(), name)
        )
        project_id = cursor.lastrowid

    notify(current_user_id(), f"Project created: {name}")

    return jsonify({"id": project_id, "name": name}), 201


@app.patch("/api/projects/<int:project_id>")
@login_required
def toggle_project(project_id):
    with get_db() as db:
        project = db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, current_user_id())
        ).fetchone()

        if not project:
            return jsonify({"error": "Project not found"}), 404

        new_status = 0 if project["completed"] else 1

        db.execute(
            "UPDATE projects SET completed = ? WHERE id = ? AND user_id = ?",
            (new_status, project_id, current_user_id())
        )

    return jsonify({"completed": new_status})


@app.delete("/api/projects/<int:project_id>")
@login_required
def delete_project(project_id):
    with get_db() as db:
        cursor = db.execute(
            "DELETE FROM projects WHERE id = ? AND user_id = ?",
            (project_id, current_user_id())
        )

    if cursor.rowcount == 0:
        return jsonify({"error": "Project not found"}), 404

    return jsonify({"message": "Project deleted"})


# ---------------- TASKS ----------------

@app.get("/api/tasks")
@login_required
def get_tasks():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
            (current_user_id(),)
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.post("/api/tasks")
@login_required
def create_task():
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    priority = data.get("priority", "Medium")
    due_date = data.get("due_date", "")

    if not name:
        return jsonify({"error": "Task name is required"}), 400

    if priority not in ("Low", "Medium", "High"):
        return jsonify({"error": "Invalid priority"}), 400

    with get_db() as db:
        cursor = db.execute(
            """INSERT INTO tasks (user_id, name, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            (current_user_id(), name, priority, due_date)
        )
        task_id = cursor.lastrowid

    notify(current_user_id(), f"Task created: {name}")

    return jsonify({"id": task_id, "name": name}), 201


@app.patch("/api/tasks/<int:task_id>")
@login_required
def toggle_task(task_id):
    with get_db() as db:
        task = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, current_user_id())
        ).fetchone()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        new_status = 0 if task["completed"] else 1

        db.execute(
            "UPDATE tasks SET completed = ? WHERE id = ? AND user_id = ?",
            (new_status, task_id, current_user_id())
        )

    return jsonify({"completed": new_status})


@app.delete("/api/tasks/<int:task_id>")
@login_required
def delete_task(task_id):
    with get_db() as db:
        cursor = db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, current_user_id())
        )

    if cursor.rowcount == 0:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({"message": "Task deleted"})


# ---------------- MESSAGES ----------------

@app.get("/api/messages")
@login_required
def get_messages():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM messages WHERE user_id = ? ORDER BY id DESC",
            (current_user_id(),)
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.post("/api/messages")
@login_required
def create_message():
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO messages (user_id, message) VALUES (?, ?)",
            (current_user_id(), message)
        )
        message_id = cursor.lastrowid

    return jsonify({"id": message_id, "message": message}), 201


@app.delete("/api/messages/<int:message_id>")
@login_required
def delete_message(message_id):
    with get_db() as db:
        cursor = db.execute(
            "DELETE FROM messages WHERE id = ? AND user_id = ?",
            (message_id, current_user_id())
        )

    if cursor.rowcount == 0:
        return jsonify({"error": "Message not found"}), 404

    return jsonify({"message": "Message deleted"})


# ---------------- DOCUMENTS ----------------

@app.get("/api/documents")
@login_required
def get_documents():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY id DESC",
            (current_user_id(),)
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.post("/api/documents")
@login_required
def upload_document():
    file = request.files.get("file")

    if not file or file.filename == "":
        return jsonify({"error": "Choose a file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    original_name = secure_filename(file.filename)
    stored_name = secure_filename(f"{current_user_id()}_{os.urandom(8).hex()}_{original_name}")

    file.save(UPLOAD_FOLDER / stored_name)

    with get_db() as db:
        cursor = db.execute(
            """INSERT INTO documents (user_id, original_name, stored_name)
               VALUES (?, ?, ?)""",
            (current_user_id(), original_name, stored_name)
        )
        document_id = cursor.lastrowid

    notify(current_user_id(), f"Document uploaded: {original_name}")

    return jsonify({"id": document_id, "name": original_name}), 201


@app.delete("/api/documents/<int:document_id>")
@login_required
def delete_document(document_id):
    with get_db() as db:
        document = db.execute(
            "SELECT * FROM documents WHERE id = ? AND user_id = ?",
            (document_id, current_user_id())
        ).fetchone()

        if not document:
            return jsonify({"error": "Document not found"}), 404

        file_path = UPLOAD_FOLDER / document["stored_name"]

        if file_path.exists():
            file_path.unlink()

        db.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?",
            (document_id, current_user_id())
        )

    return jsonify({"message": "Document deleted"})


# ---------------- NOTIFICATIONS ----------------

@app.get("/api/notifications")
@login_required
def get_notifications():
    with get_db() as db:
        rows = db.execute(
            """SELECT * FROM notifications
               WHERE user_id = ?
               ORDER BY id DESC LIMIT 50""",
            (current_user_id(),)
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.delete("/api/notifications")
@login_required
def clear_notifications():
    with get_db() as db:
        db.execute(
            "DELETE FROM notifications WHERE user_id = ?",
            (current_user_id(),)
        )

    return jsonify({"message": "Notifications cleared"})


# ---------------- HEALTH CHECK ----------------

@app.get("/api/health")
def health():
    return jsonify({"status": "healthy", "app": "Client Portal"})


# ---------------- RUN ----------------

init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
