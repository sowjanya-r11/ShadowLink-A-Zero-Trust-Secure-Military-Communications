import socket
import requests
from shadowlink_protocol import create_packet

FLASK_URL = "http://127.0.0.1:5000"
HOST = "127.0.0.1"
PORT = 9000

# Step 1 — Login and get JWT
username = input("Username: ")
password = input("Password: ")

response = requests.post(f"{FLASK_URL}/login", json={
    "username": username,
    "password": password
})

if response.status_code != 200:
    print("Login failed:", response.json()["message"])
    exit()

token = response.json()["token"]
print(f"Login successful — token received")

# Step 2 — Send Ghost Packet
mission = input("Enter mission: ")
session_id = "98234"
packet = create_packet(session_id, mission)

# Prepend token to packet
full_packet = f"{token}|{packet}"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
client.send(full_packet.encode())

response = client.recv(1024)
print("Server response:", response.decode())
client.close()