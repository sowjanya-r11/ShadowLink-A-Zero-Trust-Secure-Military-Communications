import sqlite3
import bcrypt
import random
import string
from shadowlink_protocol import generate_session_key

def create_user(username, password, role):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        (username, hashed.decode('utf-8'), role)
    )
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password, role FROM users WHERE username=?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        stored, role = result
        if isinstance(stored, str):
            stored = stored.encode('utf-8')
        if bcrypt.checkpw(password.encode(), stored):
            return role
    return None

def generate_credentials(node_name):
    username = node_name.lower().replace("-", "_")
    password = ''.join(random.choices(
        string.ascii_letters + string.digits, k=12
    ))
    return username, password

def create_mission(mission_name, commander, members):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Generate unique session key for this mission
    session_key = generate_session_key().hex()

    cursor.execute(
        """INSERT OR REPLACE INTO missions
           (mission_name, commander, status, session_key)
           VALUES (?, ?, 'active', ?)""",
        (mission_name, commander, session_key)
    )

    credentials = []
    for i, member in enumerate(members):
        node_name = f"{member}-{str(i+1).zfill(2)}"
        username, password = generate_credentials(node_name)
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        cursor.execute(
            """INSERT OR REPLACE INTO users
               (username, password, role) VALUES (?, ?, ?)""",
            (username, hashed.decode('utf-8'), 'soldier')
        )
        cursor.execute(
            """INSERT OR REPLACE INTO nodes
               (node_name, username, mission_name, status, trust_score)
               VALUES (?, ?, ?, 'offline', 100)""",
            (node_name, username, mission_name)
        )
        credentials.append({
            "node_name": node_name,
            "username": username,
            "password": password
        })

    conn.commit()
    conn.close()
    return credentials

def get_session_key(mission_name):
    """Get the AES session key for a mission"""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_key FROM missions WHERE mission_name=?",
        (mission_name,)
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return bytes.fromhex(result[0])
    return None

def close_mission(mission_name):
    """Close mission and self-destruct all credentials"""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get all usernames in this mission
    cursor.execute(
        "SELECT username FROM nodes WHERE mission_name=?",
        (mission_name,)
    )
    usernames = [row[0] for row in cursor.fetchall()]

    # Delete all soldier users
    for username in usernames:
        cursor.execute(
            "DELETE FROM users WHERE username=?",
            (username,)
        )

    # Delete all nodes
    cursor.execute(
        "DELETE FROM nodes WHERE mission_name=?",
        (mission_name,)
    )

    # Wipe session key + mark mission closed
    cursor.execute(
        """UPDATE missions
           SET status='closed', session_key=NULL
           WHERE mission_name=?""",
        (mission_name,)
    )

    conn.commit()
    conn.close()
    print(f"[SHADOWLINK] Mission {mission_name} closed — all credentials destroyed")

def get_mission_nodes(mission_name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        """SELECT node_name, username, status, trust_score
           FROM nodes WHERE mission_name=?""",
        (mission_name,)
    )
    nodes = cursor.fetchall()
    conn.close()
    return nodes

def update_node_status(username, status):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE nodes SET status=? WHERE username=?",
        (status, username)
    )
    conn.commit()
    conn.close()

def update_trust_score(username, amount):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE nodes
           SET trust_score = MAX(0, trust_score + ?)
           WHERE username=?""",
        (amount, username)
    )
    conn.commit()
    conn.close()

def log_message(sender, receiver, mission_name, status, message=""): 
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO message_logs
           (sender, receiver, mission_name, status, message) 
           VALUES (?, ?, ?, ?, ?)""",
        (sender, receiver, mission_name, status, message) 
    )
    conn.commit()
    conn.close()