from flask import Flask, render_template, request, redirect, url_for, session
import json
import os

app = Flask(__name__)
app.secret_key = "demo_secret_key"

# --- JSON file paths ---
USERS_FILE = "users.json"
VOL_FILE = "volunteers.json"

# --- JSON helpers ---
def load_json(file_path):
    if not os.path.exists(file_path):
        if "users" in file_path:
            # Default users
            data = {
                "admin": {"password": "admin123", "role": "admin", "status": "approved"},
                "student1": {"password": "pass123", "role": "student", "status": "approved"},
                "teacher1": {"password": "teach123", "role": "teacher", "status": "pending"}
            }
        else:
            data = []
        save_json(file_path, data)
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {} if "users" in file_path else []

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# --- Load helpers ---
def load_volunteers():
    return load_json(VOL_FILE)

def save_volunteers(data):
    save_json(VOL_FILE, data)

# --- ROUTES ---

# Home page
@app.route("/")
def home():
    return render_template("home.html")

# Login (role-based)
@app.route("/login/<role>", methods=["GET", "POST"])
def login_role(role):
    error = ""
    users = load_json(USERS_FILE)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = users.get(username)
        if user and user["password"] == password:
            if user.get("status") == "pending":
                error = "Your account is pending approval."
                return render_template("login.html", error=error, role=role)
            if user["role"] != role:
                error = f"This is a {role} login. Use the correct login page."
                return render_template("login.html", error=error, role=role)
            session["username"] = username
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error, role=role)

# Signup
@app.route("/signup", methods=["GET","POST"])
def signup():
    error = ""
    users = load_json(USERS_FILE)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")
        if username in users:
            error = "Username already exists"
        else:
            # Students approved immediately, teachers/admin pending
            status = "approved" if role == "student" else "pending"
            users[username] = {"password": password, "role": role, "status": status}
            save_json(USERS_FILE, users)
            return redirect(url_for("login_role", role=role))
    return render_template("signup.html", error=error)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# Main dashboard redirect based on role
@app.route("/dashboard")
def dashboard():
    role = session.get("role")
    if role == "student":
        return redirect(url_for("student_dashboard"))
    elif role == "teacher":
        return redirect(url_for("teacher_dashboard"))
    elif role == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("home"))

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student_dashboard", methods=["GET", "POST"])
def student_dashboard():
    if session.get("role") != "student":
        return redirect(url_for("login_role", role="student"))

    volunteers = load_volunteers()

    if request.method == "POST":
        volunteers.append({
            "student": session["username"],
            "activity": request.form["activity"],
            "hours": request.form["hours"],
            "description": request.form["description"],
            "status": "pending"
        })
        save_volunteers(volunteers)

    # Pending & Approved for this student
    pending = [v for v in volunteers if v["student"]==session["username"] and v["status"]=="pending"]
    approved = [v for v in volunteers if v["student"]==session["username"] and v["status"]=="approved"]

    return render_template(
        "student_dashboard.html",
        username=session["username"],
        pending_volunteers=pending,
        approved_volunteers=approved
    )

# ---------------- TEACHER DASHBOARD ----------------
@app.route("/teacher_dashboard")
def teacher_dashboard():
    if session.get("role") != "teacher":
        return redirect(url_for("login_role", role="teacher"))

    volunteers = load_volunteers()
    pending = [v for v in volunteers if v["status"] == "pending"]

    return render_template(
        "teacher_dashboard.html",
        pending_volunteers=pending,
        all_volunteers=volunteers
    )

@app.route("/approve_volunteer/<int:index>")
def approve_volunteer(index):
    if session.get("role") != "teacher":
        return redirect(url_for("login_role", role="teacher"))

    volunteers = load_volunteers()
    if 0 <= index < len(volunteers):
        volunteers[index]["status"] = "approved"
        save_volunteers(volunteers)
    return redirect("/teacher_dashboard")

@app.route("/reject_volunteer/<int:index>")
def reject_volunteer(index):
    if session.get("role") != "teacher":
        return redirect(url_for("login_role", role="teacher"))

    volunteers = load_volunteers()
    if 0 <= index < len(volunteers):
        volunteers[index]["status"] = "rejected"
        save_volunteers(volunteers)
    return redirect("/teacher_dashboard")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login_role", role="admin"))

    users = load_json(USERS_FILE)
    volunteers = load_volunteers()

    # Pending teachers or students
    pending_teachers = [u for u,v in users.items() if v["role"]=="teacher" and v["status"]=="pending"]
    pending_students = [u for u,v in users.items() if v["role"]=="student" and v["status"]=="pending"]

    # Format users for template
    users_list = [{"username": u, "role": v["role"], "status": v["status"]} for u,v in users.items()]

    return render_template(
        "admin_dashboard.html",
        users=users_list,
        volunteers=volunteers,
        pending_teachers=pending_teachers,
        pending_students=pending_students
    )

@app.route("/approve_teacher/<username>")
def approve_teacher(username):
    if session.get("role") != "admin":
        return redirect(url_for("login_role", role="admin"))
    users = load_json(USERS_FILE)
    if username in users and users[username]["role"]=="teacher":
        users[username]["status"] = "approved"
        save_json(USERS_FILE, users)
    return redirect("/admin_dashboard")

@app.route("/reject_teacher/<username>")
def reject_teacher(username):
    if session.get("role") != "admin":
        return redirect(url_for("login_role", role="admin"))
    users = load_json(USERS_FILE)
    if username in users and users[username]["role"]=="teacher":
        del users[username]
        save_json(USERS_FILE, users)
    return redirect("/admin_dashboard")

@app.route("/approve_student/<username>")
def approve_student(username):
    if session.get("role") != "admin":
        return redirect(url_for("login_role", role="admin"))
    users = load_json(USERS_FILE)
    if username in users and users[username]["role"]=="student":
        users[username]["status"] = "approved"
        save_json(USERS_FILE, users)
    return redirect("/admin_dashboard")

@app.route("/reject_student/<username>")
def reject_student(username):
    if session.get("role") != "admin":
        return redirect(url_for("login_role", role="admin"))
    users = load_json(USERS_FILE)
    if username in users and users[username]["role"]=="student":
        del users[username]
        save_json(USERS_FILE, users)
    return redirect("/admin_dashboard")
# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)