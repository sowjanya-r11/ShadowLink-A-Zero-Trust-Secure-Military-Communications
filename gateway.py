import socket
import threading
import hashlib
import time
import jwt
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from auth import update_node_status, update_trust_score, log_message

SECRET_KEY = b'ghostprotocolkey'
JWT_SECRET = "ghostsecret"
HOST = "127.0.0.1"
PORT = 9000
BLOCK_THRESHOLD = 40
REPLAY_WINDOW = 30

# Active node registry
# Format: { username: { "conn": conn, "node_name": str, "mission": str } }
active_nodes = {}
active_nodes_lock = threading.Lock()

def register_node(username, node_name, mission, conn):
    with active_nodes_lock:
        active_nodes[username] = {
            "conn": conn,
            "node_name": node_name,
            "mission": mission
        }
    update_node_status(username, "online")
    print(f"[REGISTERED] {node_name} ({username}) — Mission: {mission}")

def unregister_node(username):
    with active_nodes_lock:
        if username in active_nodes:
            del active_nodes[username]
    update_node_status(username, "offline")
    print(f"[OFFLINE] {username} disconnected")

def route_message(sender_username, receiver_node, message, mission):
    # Find receiver in active nodes
    with active_nodes_lock:
        target = None
        for uname, info in active_nodes.items():
            if info["node_name"] == receiver_node and info["mission"] == mission:
                target = (uname, info["conn"])
                break

    if not target:
        print(f"[ROUTING] {receiver_node} not found or offline")
        log_message(sender_username, receiver_node, mission, "failed")
        return False

    try:
        target_conn = target[1]
        routed_msg = f"[FROM {sender_username}] {message}"
        target_conn.send(routed_msg.encode())
        log_message(sender_username, receiver_node, mission, "delivered")
        print(f"[ROUTED] {sender_username} → {receiver_node}")
        return True
    except Exception as e:
        print(f"[ROUTING ERROR] {e}")
        log_message(sender_username, receiver_node, mission, "failed")
        return False

def broadcast_message(sender_username, message, mission):
    print(f"[BROADCAST] {sender_username} → all nodes in {mission}")
    with active_nodes_lock:
        targets = [(uname, info["conn"], info["node_name"])
                   for uname, info in active_nodes.items()
                   if info["mission"] == mission and uname != sender_username]

    success_count = 0
    for uname, conn, node_name in targets:
        try:
            broadcast_msg = f"[BROADCAST FROM {sender_username}] {message}"
            conn.send(broadcast_msg.encode())
            log_message(sender_username, node_name, mission, "delivered")
            success_count += 1
        except Exception as e:
            print(f"[BROADCAST ERROR] to {node_name}: {e}")
            log_message(sender_username, node_name, mission, "failed")

    print(f"[BROADCAST] Delivered to {success_count}/{len(targets)} nodes")

def handle_client(conn, addr):
    client_ip = addr[0]
    username = None
    print(f"\n[CONNECTION] {addr}")

    try:
        # First message must be registration
        # Format: REGISTER|token|node_name|mission
        try:
            reg_data = conn.recv(4096).decode('utf-8', errors='ignore').strip()
        except Exception as e:
            print(f"[ERROR] Failed to read registration data: {e}")
            conn.close()
            return
        reg_parts = reg_data.split("|")

        if reg_parts[0] != "REGISTER" or len(reg_parts) != 4:
            print("[ERROR] Invalid registration format")
            conn.close()
            return

        _, token, node_name, mission = reg_parts

        # Validate JWT
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            username = decoded["username"]
            print(f"[AUTH] {node_name} authenticated as {username}")
        except jwt.ExpiredSignatureError:
            print("[AUTH] Token expired")
            conn.send(b"ERROR|Token expired")
            conn.close()
            return
        except jwt.InvalidTokenError:
            print("[AUTH] Invalid token")
            conn.send(b"ERROR|Invalid token")
            conn.close()
            return

        # Register node
        register_node(username, node_name, mission, conn)
        conn.send(b"REGISTERED|Welcome to PhantomMesh")

        # Now handle incoming packets
        while True:
            try:
                data = conn.recv(4096).decode('utf-8', errors='ignore').strip()
            except Exception as e:
                print(f"[ERROR] Failed to decode packet: {e}")
                break
            if not data:
                break

            print(f"\n[PACKET] Received from {node_name}")

            # Check trust score
            import sqlite3
            db = sqlite3.connect("database.db")
            cur = db.cursor()
            cur.execute("SELECT trust_score FROM nodes WHERE username=?", (username,))
            result = cur.fetchone()
            db.close()

            if result and result[0] < BLOCK_THRESHOLD:
                print(f"[BLOCKED] {node_name} trust score too low")
                conn.send(b"BLOCKED|Trust score too low")
                log_message(username, "gateway", mission, "blocked")
                break

            # Parse packet
            # Format: token|GHOST|session|timestamp|payload|hash|destination
            parts = data.split("|")
            if len(parts) != 7:
                print("[ERROR] Invalid packet format")
                update_trust_score(username, -20)
                log_message(username, "unknown", mission, "blocked")
                continue

            pkt_token = parts[0]
            protocol  = parts[1]
            session   = parts[2]
            timestamp = parts[3]
            encrypted_payload = parts[4]
            received_hash = parts[5]
            destination = parts[6]

            # Verify JWT
            try:
                jwt.decode(pkt_token, JWT_SECRET, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                print("[AUTH] Token expired")
                update_trust_score(username, -30)
                log_message(username, destination, mission, "blocked")
                continue
            except jwt.InvalidTokenError:
                print("[AUTH] Invalid token")
                update_trust_score(username, -40)
                log_message(username, destination, mission, "blocked")
                continue

            # Integrity check
            hash_input = protocol + session + timestamp + encrypted_payload
            computed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            if computed_hash != received_hash:
                print("[TAMPER] Integrity check failed")
                update_trust_score(username, -40)
                log_message(username, destination, mission, "blocked")
                conn.send(b"ERROR|Tampered packet detected")
                continue

            # Replay check
            current_time = int(time.time())
            packet_time = int(timestamp)
            if abs(current_time - packet_time) > REPLAY_WINDOW:
                print("[REPLAY] Packet too old")
                update_trust_score(username, -30)
                log_message(username, destination, mission, "blocked")
                conn.send(b"ERROR|Replay attack detected")
                continue

            # Decrypt
            raw = bytes.fromhex(encrypted_payload)
            iv = raw[:16]
            encrypted = raw[16:]
            cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
            message = decrypted.decode()

            print(f"[DECRYPTED] {node_name} → {destination}: {message}")

            # Route message
            if destination == "BROADCAST":
                broadcast_message(username, message, mission)
                conn.send(b"OK|Broadcast delivered")
            else:
                success = route_message(username, destination, message, mission)
                if success:
                    conn.send(b"OK|Message delivered")
                else:
                    conn.send(b"ERROR|Destination offline")

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if username:
            unregister_node(username)
        conn.close()

# ─── Start Gateway ───────────────────────────────────
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()
print("=" * 50)
print("  SHADOWLINK GATEWAY")
print("  Listening on", HOST, ":", PORT)
print("=" * 50)

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.daemon = True
    thread.start()