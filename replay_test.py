import socket
import requests
import time
from shadowlink_protocol import create_packet

FLASK_URL = "http://127.0.0.1:5000"
HOST = "127.0.0.1"
PORT = 9000
MISSION = "Operation Phantom"
NODE_NAME = "REPLAY-TEST-01"

# -------------------------------
# STEP 1 — LOGIN
# -------------------------------
print("[STEP 1] Logging in...")

response = requests.post(f"{FLASK_URL}/login", json={
    "username": "commander1",
    "password": "securepass"
})

print("[DEBUG STATUS]", response.status_code)
print("[DEBUG RESPONSE]", response.text)

# Safe JSON parsing
try:
    data = response.json()
except Exception:
    print("[ERROR] Response is not valid JSON")
    exit()

if "token" not in data:
    print("[AUTH ERROR]", data)
    exit()

token = data["token"]
print("[AUTH] Login successful\n")

# -------------------------------
# STEP 2 — CONNECT TO GATEWAY
# -------------------------------
print("[STEP 2] Connecting to gateway...")

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print("[CONNECT] Connected to gateway\n")
except Exception as e:
    print("[CONNECTION ERROR]", e)
    exit()

# -------------------------------
# STEP 3 — REGISTER NODE
# -------------------------------
print("[STEP 3] Registering node...")

reg_message = f"REGISTER|{token}|{NODE_NAME}|{MISSION}"
client.send(reg_message.encode())

reg_response = client.recv(4096).decode()
print(f"[GATEWAY] {reg_response}\n")

# -------------------------------
# STEP 4 — CREATE PACKET
# -------------------------------
print("[STEP 4] Creating packet...")

session_id = "98234"
message = "Extract target from grid 7-Delta"

packet = create_packet(session_id, message)
full_packet = f"{token}|{packet}|BROADCAST"

print("[PACKET CREATED]")
print(full_packet)

# -------------------------------
# STEP 5 — WAIT (REPLAY ATTACK)
# -------------------------------
print("\n[STEP 5] Waiting to simulate replay attack...")
print("[INFO] Sleeping 15 seconds (replay window = 10s)")

time.sleep(15)

# -------------------------------
# STEP 6 — SEND OLD PACKET
# -------------------------------
print("\n[STEP 6] Sending stale packet...")

client.send(full_packet.encode())

try:
    response = client.recv(4096).decode()
except Exception as e:
    print("[ERROR RECEIVING RESPONSE]", e)
    client.close()
    exit()

print(f"\n[GATEWAY RESPONSE] {response}")

# -------------------------------
# STEP 7 — RESULT CHECK
# -------------------------------
if (
    "Replay" in response or
    "expired" in response.lower() or
    "invalid" in response.lower() or
    "ERROR" in response
):
    print("[RESULT] PASS — Replay attack detected and rejected")
else:
    print("[RESULT] FAIL — Replay attack was not caught")

client.close()
print("\n[TEST COMPLETE]")