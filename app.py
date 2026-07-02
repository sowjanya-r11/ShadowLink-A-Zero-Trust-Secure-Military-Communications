from flask import Flask, request, jsonify, render_template
from auth import verify_user, create_mission, close_mission, get_mission_nodes
from honeypot import get_attacker_profiles, get_deception_logs
from database import init_db
import jwt
import datetime
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SHADOWLINK_SECRET_KEY", "shadowlink-secret-2024")
JWT_SECRET = os.environ.get("SHADOWLINK_JWT_SECRET", "ghostsecret")

# Ensure DB and all tables exist on startup
init_db()


# ─── Deception Data ──────────────────────────────────
@app.route("/deception/profiles")
def deception_profiles():
    profiles = get_attacker_profiles()
    return jsonify({"profiles": profiles})

@app.route("/deception/logs")
def deception_logs_route():
    logs = get_deception_logs()
    return jsonify({"logs": logs})

# ─── Home ───────────────────────────────────────────
@app.route("/")
def home():
    return render_template("login.html")   # ← serves login page at root

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/soldier")
def soldier_dashboard():
    return render_template("soldier_dashboard.html")

# ─── Login ──────────────────────────────────────────
@app.route("/auth/login", methods=["POST"])  
def login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    requested_role = data.get("role", "")

    if not username or not password:
        return jsonify({"status": "error", "message": "⚠ USERNAME AND PASSWORD REQUIRED"}), 400

    # 1. Verify credentials
    role = verify_user(username, password)

    if not role:
        return jsonify({
            "status": "error",
            "message": "⚠ ACCESS DENIED — INVALID CREDENTIALS"
        }), 401
    
    # 2. Check Trust Score in Database
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        # Note: Using the 'users' table or 'nodes' table depending on where you store scores
        cursor.execute("SELECT trust_score FROM nodes WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0] <= 0:
            return jsonify({
                "status": "error", 
                "message": "⚠ CRITICAL: NODE TERMINATED BY COMMANDER. ACCESS FORBIDDEN."
            }), 403 
            
    except Exception as e:
        print(f"[DATABASE ERROR] Could not verify trust score: {e}")

    # 3. Role mismatch check (Moved up)
    if requested_role and role != requested_role:
        return jsonify({
            "status": "error",
            "message": f"⚠ ACCESS DENIED — INCORRECT ACCESS LEVEL"
        }), 401

    # 4. Generate Token and Final Success Response
    token = jwt.encode({
        "username": username,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, JWT_SECRET, algorithm="HS256")

    return jsonify({
        "status": "success",
        "token": token,
        "role": role,
        "username": username,
        "message": "Login successful"
    })

# ─── Logout ──────────────────────────────────────────
@app.route("/auth/logout")
def logout():
    return render_template("login.html")   # just redirect back to login

# ─── Create Mission ─────────────────────────────────
@app.route("/mission/create", methods=["POST"])
def create_mission_route():
    data = request.json
    mission_name = data["mission_name"]
    commander = data["commander"]
    members = data["members"]  # list of member names

    if not mission_name or not commander or not members:
        return jsonify({
            "status": "error",
            "message": "mission_name, commander and members are required"
        }), 400

    credentials = create_mission(mission_name, commander, members)
    return jsonify({
        "status": "success",
        "message": f"Mission {mission_name} created",
        "commander": commander,
        "total_nodes": len(credentials),
        "credentials": credentials
    })

# ─── Close Mission ───────────────────────────────────
@app.route("/mission/close", methods=["POST"])
def close_mission_route():
    data = request.json
    mission_name = data["mission_name"]
    close_mission(mission_name)
    return jsonify({
        "status": "success",
        "message": f"Mission {mission_name} closed"
    })

# ─── Delete Mission ───────────────────────────────────
@app.route("/mission/delete", methods=["POST"])
def delete_mission_route():
    data = request.json
    mission_name = data.get("mission_name", "").strip()
    if not mission_name:
        return jsonify({"status": "error", "message": "mission_name required"}), 400
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        # Delete all soldier users belonging to this mission
        cursor.execute("SELECT username FROM nodes WHERE mission_name=?", (mission_name,))
        usernames = [row[0] for row in cursor.fetchall()]
        for uname in usernames:
            cursor.execute("DELETE FROM users WHERE username=?", (uname,))
        # Delete nodes, message logs, and mission record
        cursor.execute("DELETE FROM nodes WHERE mission_name=?", (mission_name,))
        cursor.execute("DELETE FROM message_logs WHERE mission_name=?", (mission_name,))
        cursor.execute("DELETE FROM missions WHERE mission_name=?", (mission_name,))
        conn.commit()
        conn.close()
        print(f"[SHADOWLINK] Mission {mission_name} permanently deleted")
        return jsonify({
            "status": "success",
            "message": f"Mission {mission_name} permanently deleted — all credentials destroyed"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ─── Get Mission Nodes ───────────────────────────────
@app.route("/mission/nodes", methods=["GET"])
def get_nodes():
    mission_name = request.args.get("mission")
    if not mission_name:
        return jsonify({
            "status": "error",
            "message": "mission parameter required"
        }), 400
    nodes = get_mission_nodes(mission_name)
    node_list = []
    for node in nodes:
        node_list.append({
            "node_name": node[0],
            "username": node[1],
            "status": node[2],
            "trust_score": node[3]
        })
    return jsonify({
        "status": "success",
        "mission": mission_name,
        "nodes": node_list
    })

# ─── Block Node ──────────────────────────────────────
@app.route("/node/block", methods=["POST"])
def block_node():
    data = request.json
    username = data["username"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE nodes SET trust_score=0 WHERE username=?",
        (username,)
    )
    conn.commit()
    conn.close()
    return jsonify({
        "status": "success",
        "message": f"{username} has been blocked"
    })

# ─── Unblock Node ─────────────────────────────────────
@app.route("/node/unblock", methods=["POST"])
def unblock_node():
    data = request.json
    username = data["username"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE nodes SET trust_score=100 WHERE username=?",
        (username,)
    )
    conn.commit()
    conn.close()
    return jsonify({
        "status": "success",
        "message": f"{username} has been unblocked"
    })


# ─── Soldier: Log Message (from soldier dashboard) ───
@app.route("/message/send", methods=["POST"])
def message_send():
    data = request.json
    sender = data.get("sender")
    receiver = data.get("receiver")
    mission_name = data.get("mission_name")
    message_content = data.get("message", "")  

    from auth import log_message
    log_message(sender, receiver, mission_name, "delivered", message_content)
    return jsonify({"status": "success"})

# ─── Soldier: Get own node info ───────────────────────
@app.route("/soldier/node", methods=["GET"])
def soldier_node():
    username = request.args.get("username")
    if not username:
        return jsonify({"status": "error", "message": "username required"}), 400
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT node_name, mission_name, status, trust_score FROM nodes WHERE username=?",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "error", "message": "node not found"}), 404
    return jsonify({
        "status": "success",
        "node_name": row[0],
        "mission_name": row[1],
        "node_status": row[2],
        "trust_score": row[3]
    })

# ─── Dashboard Alerts ────────────────────────────────
@app.route("/dashboard/alerts", methods=["GET"])
def dashboard_alerts():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT node_name, username, trust_score, mission_name
        FROM nodes
        WHERE trust_score < 40
    """)
    blocked = [{"node_name": r[0], "username": r[1],
                "trust_score": r[2], "mission_name": r[3]}
               for r in cursor.fetchall()]
    conn.close()
    return jsonify({"alerts": blocked})

# ─── Dashboard Data ──────────────────────────────────
@app.route("/dashboard/data", methods=["GET"])
def dashboard_data():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get all missions
    cursor.execute("SELECT mission_name, commander, status, created_at FROM missions")
    missions = [{"mission_name": r[0], "commander": r[1],
                 "status": r[2], "created_at": r[3]} for r in cursor.fetchall()]

    # Get all nodes
    cursor.execute("SELECT node_name, username, mission_name, status, trust_score FROM nodes")
    nodes = [{"node_name": r[0], "username": r[1], "mission_name": r[2],
              "status": r[3], "trust_score": r[4]} for r in cursor.fetchall()]

    # Get recent message logs
    cursor.execute("""
        SELECT sender, receiver, mission_name, status, timestamp, message
        FROM message_logs
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    logs = [{"sender": r[0], "receiver": r[1], "mission_name": r[2],
             "status": r[3], "timestamp": r[4], "message": r[5]} for r in cursor.fetchall()]

    # Get stats
    cursor.execute("SELECT COUNT(*) FROM missions WHERE status='active'")
    active_missions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM nodes WHERE status='online'")
    online_nodes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM message_logs WHERE status='blocked'")
    blocked_packets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM message_logs")
    total_packets = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "stats": {
            "active_missions": active_missions,
            "online_nodes": online_nodes,
            "blocked_packets": blocked_packets,
            "total_packets": total_packets
        },
        "missions": missions,
        "nodes": nodes,
        "logs": logs
    })

if __name__ == "__main__":
    print("=" * 50)
    print("  SHADOWLINK WEB INTERFACE")
    print("=" * 50)

    app.run(debug=True, use_reloader=False)