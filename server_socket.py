import socket
import hashlib
import time
import jwt
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import sqlite3

SECRET_KEY = b'ghostprotocolkey'
JWT_SECRET = "ghostsecret"
HOST = "127.0.0.1"
PORT = 9000
BLOCK_THRESHOLD = 40
REPLAY_WINDOW = 30  # seconds

def get_db_trust_score(username):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT trust_score FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return 0

trust_scores = {}

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()
print("Ghost Gateway Socket Listening...\n")

while True:
    conn, addr = server.accept()
    client_ip = addr[0]
    print("Connected by", addr)

    if client_ip not in trust_scores:
        trust_scores[client_ip] = 100

    # Firewall check
    if trust_scores[client_ip] < BLOCK_THRESHOLD:
        print(f"[BLOCKED] {client_ip} — trust score too low")
        conn.close()
        continue

    try:
        data = conn.recv(4096).decode()
        if not data:
            conn.close()
            continue

        print("\nRaw packet received:")
        print(data)

        # Expect: TOKEN|GHOST|session|timestamp|payload|hash
        parts = data.split("|")
        if len(parts) != 6:
            print("[ERROR] Invalid packet format")
            trust_scores[client_ip] -= 20
            conn.close()
            continue

        token = parts[0]
        protocol = parts[1]
        session = parts[2]
        timestamp = parts[3]
        encrypted_payload = parts[4]
        received_hash = parts[5]

        # JWT validation
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            username = decoded.get('username')
            
            # --- NEW: Check Database for Commander's Block ---
            current_db_score = get_db_trust_score(username)
            if current_db_score <= 0:
                print(f"[SECURITY ALERT] Blocked user {username} attempted access.")
                conn.send(b"ERROR: ACCOUNT TERMINATED BY COMMANDER")
                conn.close()
                continue
            # -----------------------------------------------

            print(f"[AUTH] Valid token — user: {username}, role: {decoded['role']}")
            
        except jwt.ExpiredSignatureError:
            print("[AUTH] Token expired")
            trust_scores[client_ip] -= 30
            conn.close()
            continue
        except jwt.InvalidTokenError:
            print("[AUTH] Invalid token")
            trust_scores[client_ip] -= 40
            conn.close()
            continue

        # Integrity check
        hash_input = protocol + session + timestamp + encrypted_payload
        computed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        if computed_hash != received_hash:
            print("[TAMPER] Packet integrity check failed")
            trust_scores[client_ip] -= 40
            print(f"Trust score: {trust_scores[client_ip]}")
            conn.close()
            continue

        print("[OK] Packet integrity verified")

        # Replay attack check
        current_time = int(time.time())
        packet_time = int(timestamp)
        if abs(current_time - packet_time) > REPLAY_WINDOW:
            print("[REPLAY] Packet too old — possible replay attack")
            trust_scores[client_ip] -= 30
            print(f"Trust score: {trust_scores[client_ip]}")
            conn.close()
            continue

        # CBC Decrypt
        raw = bytes.fromhex(encrypted_payload)
        iv = raw[:16]
        encrypted = raw[16:]
        cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)

        print("\n[DECRYPTED MISSION]")
        print(decrypted.decode())
        print(f"\nTrust score: {trust_scores[client_ip]}")

        conn.send(b"MISSION RECEIVED")

    except Exception as e:
        print(f"[ERROR] {e}")
        conn.close()

    