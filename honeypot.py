import socket
import threading
import sqlite3
import json
from datetime import datetime

# Honeypot ports and their fake service responses
HONEYPOT_PORTS = {
    8080: {
        "service": "Apache HTTP Server",
        "banner": "HTTP/1.1 200 OK\r\nServer: Apache/2.4.41 (Ubuntu)\r\nContent-Type: text/html\r\n\r\n<html><body><h1>ShadowLink Internal Portal</h1><p>Authentication required.</p></body></html>",
        "type": "web_server"
    },
    3306: {
        "service": "MySQL Database",
        "banner": "5.7.32-MySQL Community Server\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        "type": "database"
    },
    2222: {
        "service": "OpenSSH",
        "banner": "SSH-2.0-OpenSSH_7.4\r\nInvalid credentials. Connection logged.\r\n",
        "type": "ssh"
    },
    8888: {
        "service": "FTP Server",
        "banner": "220 ShadowLink FTP Server Ready\r\n331 Password required\r\n",
        "type": "ftp"
    }
}

# In memory attacker tracking
attacker_profiles = {}
attacker_lock = threading.Lock()

def log_deception(attacker_ip, port, attempt_type, data_sent, fake_response):
    """Log every honeypot interaction to database"""
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deception_logs
            (attacker_ip, port_accessed, attempt_type, data_sent, fake_response)
            VALUES (?, ?, ?, ?, ?)
        """, (attacker_ip, port, attempt_type, data_sent, fake_response))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[HONEYPOT] Log error: {e}")

def update_attacker_profile(attacker_ip, port, data):
    """Build behavioral profile of attacker"""
    with attacker_lock:
        if attacker_ip not in attacker_profiles:
            attacker_profiles[attacker_ip] = {
                "ports_scanned": [],
                "total_attempts": 0,
                "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_seen": None,
                "commands_tried": [],
                "behavior_type": "unknown"
            }

        profile = attacker_profiles[attacker_ip]
        profile["total_attempts"] += 1
        profile["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if port not in profile["ports_scanned"]:
            profile["ports_scanned"].append(port)

        if data and data not in profile["commands_tried"]:
            profile["commands_tried"].append(data[:100])

        # Behavioral analysis
        ports_count = len(profile["ports_scanned"])
        attempts = profile["total_attempts"]

        if ports_count >= 3:
            profile["behavior_type"] = "port_scanner"
        elif attempts >= 5:
            profile["behavior_type"] = "brute_force"
        elif "admin" in str(data).lower() or "root" in str(data).lower():
            profile["behavior_type"] = "credential_stuffer"
        elif attempts >= 2:
            profile["behavior_type"] = "reconnaissance"
        else:
            profile["behavior_type"] = "probe"

        # Save to database
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attacker_profiles
                (attacker_ip, ports_scanned, total_attempts,
                 first_seen, last_seen, behavior_type)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(attacker_ip) DO UPDATE SET
                    ports_scanned=excluded.ports_scanned,
                    total_attempts=excluded.total_attempts,
                    last_seen=excluded.last_seen,
                    behavior_type=excluded.behavior_type
            """, (
                attacker_ip,
                json.dumps(profile["ports_scanned"]),
                profile["total_attempts"],
                profile["first_seen"],
                profile["last_seen"],
                profile["behavior_type"]
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[HONEYPOT] Profile update error: {e}")

        return profile

def generate_fake_credentials():
    """Generate fake credentials to feed attackers"""
    return {
        "username": "shadow_admin",
        "password": "ShadowLink@2024",
        "api_key": "sl_fake_key_9x2k4m8n1p",
        "note": "INTERNAL USE ONLY — ShadowLink Command Access"
    }

def handle_honeypot_connection(conn, addr, port, service_info):
    """Handle a single honeypot connection"""
    attacker_ip = addr[0]
    service_name = service_info["service"]
    banner = service_info["banner"]
    service_type = service_info["type"]

    print(f"\n[HONEYPOT] ⚠ Connection on port {port} ({service_name})")
    print(f"[HONEYPOT] Attacker IP: {attacker_ip}")

    try:
        # Send fake banner
        conn.send(banner.encode() if isinstance(banner, str) else banner)

        # Receive attacker's data
        conn.settimeout(10)
        try:
            data = conn.recv(1024).decode(errors='ignore').strip()
        except:
            data = ""

        print(f"[HONEYPOT] Attacker sent: {repr(data)}")

        # Update profile
        profile = update_attacker_profile(attacker_ip, port, data)

        # Generate fake response based on service type
        if service_type == "web_server":
            if "admin" in data.lower() or "login" in data.lower():
                fake_creds = generate_fake_credentials()
                fake_response = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: application/json\r\n\r\n"
                    f"{json.dumps(fake_creds)}"
                )
            else:
                fake_response = (
                    "HTTP/1.1 403 Forbidden\r\n"
                    "Content-Type: text/html\r\n\r\n"
                    "<html><body>Access restricted. "
                    "This attempt has been logged.</body></html>"
                )

        elif service_type == "database":
            fake_response = (
                "ERROR 1045: Access denied for user "
                "'attacker'@'localhost' (using password: YES)"
            )

        elif service_type == "ssh":
            fake_response = (
                "Permission denied (publickey,password).\r\n"
                "Warning: Unauthorized access attempt logged.\r\n"
            )

        elif service_type == "ftp":
            fake_response = (
                "530 Login incorrect.\r\n"
                "421 Too many failed attempts — IP logged.\r\n"
            )

        else:
            fake_response = "Connection refused: Unauthorized access detected."

        # Send fake response
        conn.send(fake_response.encode())

        # Log everything
        log_deception(
            attacker_ip, port,
            profile["behavior_type"],
            data, fake_response
        )

        print(f"[HONEYPOT] Behavior: {profile['behavior_type']}")
        print(f"[HONEYPOT] Total attempts from {attacker_ip}: "
              f"{profile['total_attempts']}")
        print(f"[HONEYPOT] Ports probed: {profile['ports_scanned']}")

    except Exception as e:
        print(f"[HONEYPOT] Error: {e}")
    finally:
        conn.close()

def start_honeypot_port(port, service_info):
    """Start a single honeypot listener on a port"""
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", port))
        server.listen(5)
        print(f"[HONEYPOT] Fake {service_info['service']} on port {port}")

        while True:
            conn, addr = server.accept()
            thread = threading.Thread(
                target=handle_honeypot_connection,
                args=(conn, addr, port, service_info)
            )
            thread.daemon = True
            thread.start()

    except PermissionError:
        print(f"[HONEYPOT] Port {port} requires sudo — skipping")
    except Exception as e:
        print(f"[HONEYPOT] Port {port} error: {e}")

def get_attacker_profiles():
    """Return all attacker profiles from database"""
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attacker_ip, ports_scanned, total_attempts,
                   first_seen, last_seen, behavior_type
            FROM attacker_profiles
            ORDER BY last_seen DESC
        """)
        profiles = []
        for row in cursor.fetchall():
            profiles.append({
                "attacker_ip": row[0],
                "ports_scanned": json.loads(row[1]) if row[1] else [],
                "total_attempts": row[2],
                "first_seen": row[3],
                "last_seen": row[4],
                "behavior_type": row[5]
            })
        conn.close()
        return profiles
    except Exception as e:
        print(f"[HONEYPOT] Profile fetch error: {e}")
        return []

def get_deception_logs():
    """Return recent deception logs"""
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attacker_ip, port_accessed, attempt_type,
                   data_sent, fake_response, timestamp
            FROM deception_logs
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        logs = []
        for row in cursor.fetchall():
            logs.append({
                "attacker_ip": row[0],
                "port": row[1],
                "attempt_type": row[2],
                "data_sent": row[3],
                "fake_response": row[4][:80] + "..." if row[4] and len(row[4]) > 80 else row[4],
                "timestamp": row[5]
            })
        conn.close()
        return logs
    except Exception as e:
        print(f"[HONEYPOT] Log fetch error: {e}")
        return []

def start_honeypot():
    """Start all honeypot listeners"""
    print("=" * 50)
    print("  SHADOWLINK DECEPTION ENGINE")
    print("  Active Honeypot System")
    print("=" * 50)

    threads = []
    for port, service_info in HONEYPOT_PORTS.items():
        t = threading.Thread(
            target=start_honeypot_port,
            args=(port, service_info)
        )
        t.daemon = True
        threads.append(t)
        t.start()

    print(f"\n[HONEYPOT] {len(HONEYPOT_PORTS)} fake services running")
    print("[HONEYPOT] Waiting for attackers...\n")

    # Keep main thread alive
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n[HONEYPOT] Shutting down deception engine")

if __name__ == "__main__":
    start_honeypot()