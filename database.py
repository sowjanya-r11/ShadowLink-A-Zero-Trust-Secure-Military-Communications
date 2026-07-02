import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    # Missions table — added session_key column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_name TEXT UNIQUE,
            commander TEXT,
            status TEXT DEFAULT 'active',
            session_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Nodes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT UNIQUE,
            username TEXT,
            mission_name TEXT,
            status TEXT DEFAULT 'offline',
            trust_score INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Message logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS message_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        mission_name TEXT,
        status TEXT,
        message TEXT,  -- <--- ADD THIS COLUMN
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

    # Deception logs table — NEW
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deception_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_ip TEXT,
            port_accessed INTEGER,
            attempt_type TEXT,
            data_sent TEXT,
            fake_response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Attacker profiles table — NEW
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attacker_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_ip TEXT UNIQUE,
            ports_scanned TEXT,
            total_attempts INTEGER DEFAULT 0,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            behavior_type TEXT DEFAULT 'unknown'
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("ShadowLink database initialized.")