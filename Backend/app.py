from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_cors import CORS
from datetime import date, timedelta
import mysql.connector
import bcrypt
from functools import wraps

app = Flask(__name__)
app.secret_key = "fitquest_secret_2024"
CORS(app, supports_credentials=True)

# ─────────────────────────────────────────────
# DATABASE — change password to yours!
# ─────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sreerag@2025",  # ← YOUR MYSQL PASSWORD HERE
        database="fitquest"
    )

# ─────────────────────────────────────────────
# LOGIN REQUIRED
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# GAMIFICATION
# ─────────────────────────────────────────────
def award_points(user_id, points, db, cursor):
    cursor.execute("UPDATE Progress SET Total_Points = Total_Points + %s WHERE User_ID = %s", (points, user_id))
    cursor.execute("UPDATE Progress SET Level_Status = FLOOR(Total_Points / 1000) + 1 WHERE User_ID = %s", (user_id,))
    today = date.today()
    cursor.execute("SELECT Last_Active_Date, Streak_Days FROM Progress WHERE User_ID = %s", (user_id,))
    row = cursor.fetchone()
    if row:
        last_active, streak = row
        new_streak = streak + 1 if last_active == today - timedelta(days=1) else (streak if last_active == today else 1)
        cursor.execute("UPDATE Progress SET Streak_Days = %s, Last_Active_Date = %s WHERE User_ID = %s", (new_streak, today, user_id))
        for days, badge in [(7,'7-Day Consistency'),(30,'Streak Master')]:
            if new_streak >= days:
                cursor.execute("SELECT Badge_ID FROM Badges WHERE Badge_Name = %s", (badge,))
                b = cursor.fetchone()
                if b: cursor.execute("INSERT IGNORE INTO User_Badges (User_ID, Badge_ID) VALUES (%s, %s)", (user_id, b[0]))
    cursor.execute("SELECT Total_Points FROM Progress WHERE User_ID = %s", (user_id,))
    total = cursor.fetchone()
    if total and total[0] >= 100:
        cursor.execute("SELECT Badge_ID FROM Badges WHERE Badge_Name = 'First Step'")
        b = cursor.fetchone()
        if b: cursor.execute("INSERT IGNORE INTO User_Badges (User_ID, Badge_ID) VALUES (%s, %s)", (user_id, b[0]))
    db.commit()


# ═══════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

@app.route('/diet')
def diet_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('diet.html')

@app.route('/exercise')
def exercise_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('exercise.html')

@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('profile.html')


# ═══════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    # All questions collected in register form
    required = ["name", "age", "gender", "email", "password", "height_cm", "weight_kg", "fitness_goal"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO Users (Name, Age, Gender, Height_cm, Weight_kg, Fitness_Goal, Email, Password_Hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (data["name"], data["age"], data["gender"],
              data["height_cm"], data["weight_kg"],
              data["fitness_goal"], data["email"], hashed))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO Progress (User_ID, Last_Active_Date) VALUES (%s, %s)", (user_id, date.today()))
        db.commit()
        return jsonify({"message": "Registered successfully!", "user_id": user_id}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    finally:
        cursor.close()
        db.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Users WHERE Email = %s", (data["email"],))
    user = cursor.fetchone()
    cursor.close()
    db.close()
    if not user or not bcrypt.checkpw(data["password"].encode(), user["Password_Hash"].encode()):
        return jsonify({"error": "Invalid credentials"}), 401
    session["user_id"] = user["User_ID"]
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user["User_ID"],
            "name": user["Name"],
            "fitness_goal": user["Fitness_Goal"],
            "bmi": round(float(user["BMI"]), 2) if user["BMI"] else None
        }
    }), 200


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@app.route("/api/delete-account", methods=["DELETE"])
@login_required
def delete_account():
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM User_Badges WHERE User_ID = %s", (user_id,))
        cursor.execute("DELETE FROM Progress WHERE User_ID = %s", (user_id,))
        cursor.execute("DELETE FROM Activity_Log WHERE User_ID = %s", (user_id,))
        cursor.execute("DELETE FROM Users WHERE User_ID = %s", (user_id,))
        db.commit()
        session.clear()
        return jsonify({"message": "Account deleted"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


# ═══════════════════════════════════════════════
#  PROFILE ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/profile", methods=["GET"])
@login_required
def get_profile():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.User_ID, u.Name, u.Age, u.Gender, u.Height_cm, u.Weight_kg,
               ROUND(u.BMI, 2) AS BMI, u.Fitness_Goal, u.Is_Injured, u.Rest_Mode,
               u.Email, u.Created_At,
               p.Level_Status, p.Total_Points, p.Streak_Days, p.Badge_Earned
        FROM Users u LEFT JOIN Progress p ON u.User_ID = p.User_ID
        WHERE u.User_ID = %s
    """, (session["user_id"],))
    profile = cursor.fetchone()
    cursor.close()
    db.close()
    return jsonify(profile), 200


@app.route("/api/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.json
    allowed = ["name", "age", "height_cm", "weight_kg", "fitness_goal", "is_injured", "rest_mode"]
    updates = {k: v for k, v in data.items() if k.lower() in allowed}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    set_clause = ", ".join([f"{k} = %s" for k in updates])
    values = list(updates.values()) + [session["user_id"]]
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f"UPDATE Users SET {set_clause} WHERE User_ID = %s", values)
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"message": "Profile updated"}), 200


# ═══════════════════════════════════════════════
#  DIET ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/diet", methods=["GET"])
@login_required
def get_diet():
    region = request.args.get("region")
    meal_type = request.args.get("meal_type")
    db = get_db()
    cursor = db.cursor(dictionary=True)
    query = "SELECT * FROM Diet WHERE 1=1"
    params = []
    if region:
        query += " AND Region_Type = %s"; params.append(region)
    if meal_type:
        query += " AND Meal_Type = %s"; params.append(meal_type)
    db2 = get_db(); c2 = db2.cursor(dictionary=True)
    c2.execute("SELECT Fitness_Goal FROM Users WHERE User_ID = %s", (session["user_id"],))
    user = c2.fetchone(); c2.close(); db2.close()
    if user and user["Fitness_Goal"] == "Weight Loss":
        query += " AND Calories <= 300"
    cursor.execute(query, params)
    items = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify(items), 200


@app.route("/api/diet", methods=["POST"])
@login_required
def add_diet_item():
    data = request.json
    if not all(k in data for k in ["food_name","calories","region_type","meal_type"]):
        return jsonify({"error": "Missing fields"}), 400
    db = get_db(); cursor = db.cursor()
    cursor.execute("""INSERT INTO Diet (Food_Name, Calories, Protein_g, Carbs_g, Fat_g, Region_Type, Meal_Type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (data["food_name"], data["calories"], data.get("protein_g",0),
         data.get("carbs_g",0), data.get("fat_g",0), data["region_type"], data["meal_type"]))
    db.commit(); cursor.close(); db.close()
    return jsonify({"message": "Diet item added"}), 201


# ═══════════════════════════════════════════════
#  EXERCISE ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/exercise", methods=["GET"])
@login_required
def get_exercises():
    db = get_db(); cursor = db.cursor(dictionary=True)
    c2 = get_db().cursor(dictionary=True)
    c2.execute("SELECT Is_Injured, Rest_Mode FROM Users WHERE User_ID = %s", (session["user_id"],))
    user = c2.fetchone(); c2.close()
    if user and (user["Is_Injured"] or user["Rest_Mode"]):
        cursor.execute("SELECT * FROM Exercise WHERE Intensity = 'Low' OR Exercise_Type = 'Rest'")
    else:
        cursor.execute("SELECT * FROM Exercise")
    items = cursor.fetchall(); cursor.close(); db.close()
    return jsonify(items), 200


@app.route("/api/exercise", methods=["POST"])
@login_required
def add_exercise():
    data = request.json
    if not all(k in data for k in ["exercise_name","duration_min","calories_burned","intensity","exercise_type"]):
        return jsonify({"error": "Missing fields"}), 400
    db = get_db(); cursor = db.cursor()
    cursor.execute("""INSERT INTO Exercise (Exercise_Name, Duration_min, Calories_Burned, Intensity, Exercise_Type)
        VALUES (%s, %s, %s, %s, %s)""",
        (data["exercise_name"], data["duration_min"], data["calories_burned"], data["intensity"], data["exercise_type"]))
    db.commit(); cursor.close(); db.close()
    return jsonify({"message": "Exercise added"}), 201


# ═══════════════════════════════════════════════
#  ACTIVITY LOG ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/log", methods=["POST"])
@login_required
def log_activity():
    data = request.json
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Auto-fill calories from diet if diet_id provided and calories not manually entered
    cal = data.get("calories_consumed", 0)
    if data.get("diet_id") and not cal:
        cursor.execute("SELECT Calories FROM Diet WHERE Diet_ID = %s", (data["diet_id"],))
        row = cursor.fetchone()
        if row: cal = row["Calories"]

    # Auto-fill duration from exercise if exercise_id provided and duration not manually entered
    dur = data.get("exercise_duration_min", 0)
    if data.get("exercise_id") and not dur:
        cursor.execute("SELECT Duration_min FROM Exercise WHERE Exercise_ID = %s", (data["exercise_id"],))
        row = cursor.fetchone()
        if row: dur = row["Duration_min"]

    cursor.execute("""INSERT INTO Activity_Log
        (User_ID, Log_Date, Diet_ID, Exercise_ID, Calories_Consumed, Water_Intake_L, Exercise_Duration_min, Notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, data.get("log_date", date.today()),
         data.get("diet_id") or None,
         data.get("exercise_id") or None,
         cal,
         data.get("water_intake_l", 0),
         dur,
         data.get("notes", "")))
    db.commit()
    award_points(user_id, 50, db, cursor)
    cursor.close()
    db.close()
    return jsonify({"message": "Activity logged! +50 points earned 🎉"}), 201


@app.route("/api/log", methods=["GET"])
@login_required
def get_logs():
    user_id = session["user_id"]
    start = request.args.get("start_date")
    end = request.args.get("end_date", str(date.today()))
    db = get_db(); cursor = db.cursor(dictionary=True)
    query = """SELECT al.*, d.Food_Name, d.Calories AS Food_Calories,
               e.Exercise_Name, e.Calories_Burned
               FROM Activity_Log al
               LEFT JOIN Diet d ON al.Diet_ID = d.Diet_ID
               LEFT JOIN Exercise e ON al.Exercise_ID = e.Exercise_ID
               WHERE al.User_ID = %s"""
    params = [user_id]
    if start:
        query += " AND al.Log_Date BETWEEN %s AND %s"; params += [start, end]
    query += " ORDER BY al.Log_Date DESC"
    cursor.execute(query, params)
    logs = cursor.fetchall(); cursor.close(); db.close()
    return jsonify(logs), 200


@app.route("/api/log/<int:log_id>", methods=["DELETE"])
@login_required
def delete_log(log_id):
    db = get_db(); cursor = db.cursor()
    cursor.execute("DELETE FROM Activity_Log WHERE Log_ID = %s AND User_ID = %s", (log_id, session["user_id"]))
    db.commit(); cursor.close(); db.close()
    return jsonify({"message": "Log deleted"}), 200


# ═══════════════════════════════════════════════
#  PROGRESS & BADGES ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/progress", methods=["GET"])
@login_required
def get_progress():
    user_id = session["user_id"]
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT p.*, GROUP_CONCAT(b.Badge_Name SEPARATOR ', ') AS Badges_Earned
        FROM Progress p LEFT JOIN User_Badges ub ON p.User_ID = ub.User_ID
        LEFT JOIN Badges b ON ub.Badge_ID = b.Badge_ID
        WHERE p.User_ID = %s GROUP BY p.Progress_ID""", (user_id,))
    progress = cursor.fetchone()
    if progress:
        progress["Points_To_Next_Level"] = (progress["Level_Status"] * 1000) - progress["Total_Points"]
    cursor.close(); db.close()
    return jsonify(progress), 200


@app.route("/api/badges", methods=["GET"])
@login_required
def get_all_badges():
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT b.*, IF(ub.User_ID IS NOT NULL, TRUE, FALSE) AS Earned
        FROM Badges b LEFT JOIN User_Badges ub ON b.Badge_ID = ub.Badge_ID AND ub.User_ID = %s""",
        (session["user_id"],))
    badges = cursor.fetchall(); cursor.close(); db.close()
    return jsonify(badges), 200


# ═══════════════════════════════════════════════
#  ANALYTICS ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/analytics/calories", methods=["GET"])
@login_required
def calorie_analytics():
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT al.Log_Date,
        SUM(al.Calories_Consumed) AS Total_Consumed, SUM(e.Calories_Burned) AS Total_Burned
        FROM Activity_Log al LEFT JOIN Exercise e ON al.Exercise_ID = e.Exercise_ID
        WHERE al.User_ID = %s AND al.Log_Date >= CURDATE() - INTERVAL 30 DAY
        GROUP BY al.Log_Date ORDER BY al.Log_Date""", (session["user_id"],))
    data = cursor.fetchall(); cursor.close(); db.close()
    return jsonify(data), 200


@app.route("/api/analytics/hydration", methods=["GET"])
@login_required
def hydration_analytics():
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT Log_Date, Water_Intake_L FROM Activity_Log
        WHERE User_ID = %s AND Log_Date >= CURDATE() - INTERVAL 7 DAY
        ORDER BY Log_Date""", (session["user_id"],))
    data = cursor.fetchall(); cursor.close(); db.close()
    return jsonify(data), 200


@app.route("/api/analytics/weight", methods=["GET"])
@login_required
def weight_analytics():
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT DATE_FORMAT(Log_Date, '%Y-%m') AS Month, AVG(u.Weight_kg) AS Avg_Weight
        FROM Activity_Log al JOIN Users u ON al.User_ID = u.User_ID
        WHERE al.User_ID = %s GROUP BY Month ORDER BY Month""", (session["user_id"],))
    data = cursor.fetchall(); cursor.close(); db.close()
    return jsonify(data), 200


@app.route("/api/analytics/dashboard", methods=["GET"])
@login_required
def dashboard_summary():
    user_id = session["user_id"]
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT SUM(Calories_Consumed) AS Today_Calories,
        SUM(Water_Intake_L) AS Today_Water, SUM(Exercise_Duration_min) AS Today_Exercise_Min
        FROM Activity_Log WHERE User_ID = %s AND Log_Date = CURDATE()""", (user_id,))
    today = cursor.fetchone()
    cursor.execute("SELECT Name, ROUND(BMI,2) AS BMI, Fitness_Goal, Is_Injured, Rest_Mode FROM Users WHERE User_ID = %s", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT Level_Status, Total_Points, Streak_Days FROM Progress WHERE User_ID = %s", (user_id,))
    progress = cursor.fetchone()
    cursor.close(); db.close()
    return jsonify({"user": user, "today": today, "progress": progress}), 200


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)