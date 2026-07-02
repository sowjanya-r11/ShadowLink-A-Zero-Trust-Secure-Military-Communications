import socket
import requests
from shadowlink_protocol import create_packet

FLASK_URL = "http://127.0.0.1:5000"
HOST = "127.0.0.1"
PORT = 9000
MISSION = "Operation Shadow"
NODE_NAME = "TAMPER-TEST-01"

# Step 1 — Login and get JWT
response = requests.post(f"{FLASK_URL}/auth/login", json={
    "username": "commander1",
    "password": "admin1234"
})

data = response.json()

if "token" not in data:
    print("[AUTH ERROR]", data)
    exit()

token = data["token"]
print("[AUTH] Login successful")

# Step 2 — Connect and register with gateway
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print(f"Connecting to {HOST}:{PORT}...")
client.connect((HOST, PORT))

reg_message = f"REGISTER|{token}|{NODE_NAME}|{MISSION}"
client.send(reg_message.encode())

reg_response = client.recv(4096).decode()
print(f"[GATEWAY] {reg_response}")

# Step 3 — Create a valid packet
session_id = "98234"
message = "Extract target from grid 7-Delta"

packet = create_packet(session_id, message)
full_packet = f"{token}|{packet}|BROADCAST"

print("\n[ORIGINAL PACKET]")
print(full_packet)

# Step 4 — Tamper with ENCRYPTED PAYLOAD (correct index = 4)
parts = full_packet.split("|")

if len(parts) < 7:
    print("[ERROR] Packet format incorrect:", parts)
    client.close()
    exit()

# Tamper payload
parts[4] = "TAMPERED_PAYLOAD_000000000000000000"

tampered_packet = "|".join(parts)

print("\n[TAMPERED PACKET]")
print(tampered_packet)

# Step 5 — Send tampered packet
client.send(tampered_packet.encode())

response = client.recv(4096).decode()
print(f"\n[GATEWAY RESPONSE] {response}")

# Step 6 — Result validation
if "Tampered" in response or "ERROR" in response or "invalid" in response.lower():
    print("[RESULT] PASS — Tamper detected and rejected by gateway")
else:
    print("[RESULT] FAIL — Tamper was not caught")

client.close()