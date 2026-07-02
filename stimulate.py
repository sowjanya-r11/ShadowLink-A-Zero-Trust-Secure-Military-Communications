import requests
import socket
import threading
import time
from shadowlink_protocol import create_packet

FLASK_URL = "http://127.0.0.1:5000"
HOST = "127.0.0.1"
PORT = 9000

def create_demo_mission():
    print("\n[MISSION CONTROL] Creating demo mission...")
    response = requests.post(f"{FLASK_URL}/mission/create", json={
        "mission_name": "Operation Phantom",
        "commander": "commander1",
        "members": ["ALPHA", "BRAVO", "CHARLIE", "DELTA"]
    })
    data = response.json()
    print(f"[MISSION] {data['message']}")
    return data["credentials"]

def simulate_node(cred, all_creds, delay=0):
    """Simulates a single node connecting and sending messages"""
    time.sleep(delay)

    username = cred["username"]
    password = cred["password"]
    node_name = cred["node_name"]
    mission = "Operation Phantom"

    try:
        # Login
        response = requests.post(f"{FLASK_URL}/auth/login", json={
            "username": username,
            "password": password
        })
        if response.status_code != 200:
            print(f"[{node_name}] Login failed")
            return

        token = response.json()["token"]
        print(f"[{node_name}] Login successful")

        # Connect to gateway
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))

        # Register
        reg_message = f"REGISTER|{token}|{node_name}|{mission}"
        client.send(reg_message.encode())
        reg_response = client.recv(4096).decode()
        print(f"[{node_name}] {reg_response}")

        # Listen for incoming messages in background
        def listen():
            while True:
                try:
                    data = client.recv(4096).decode()
                    if not data:
                        break
                    print(f"[{node_name}] INCOMING: {data}")
                except:
                    break

        listener = threading.Thread(target=listen)
        listener.daemon = True
        listener.start()

        # Wait a moment then send messages
        time.sleep(2)

        # Send a direct message to next node
        other_creds = [c for c in all_creds if c["username"] != username]
        if other_creds:
            target = other_creds[0]["node_name"]
            message = f"Secure transmission from {node_name} — all systems operational"
            packet = create_packet(username, message)
            full_packet = f"{token}|{packet}|{target}"
            client.send(full_packet.encode())
            response = client.recv(4096).decode()
            print(f"[{node_name}] → {target}: {response}")

        time.sleep(2)

        # Broadcast
        broadcast_msg = f"{node_name} reporting in — mission active"
        packet = create_packet(username, broadcast_msg)
        full_packet = f"{token}|{packet}|BROADCAST"
        client.send(full_packet.encode())
        response = client.recv(4096).decode()
        print(f"[{node_name}] BROADCAST: {response}")

        # Stay connected for 15 seconds
        time.sleep(15)
        client.close()
        print(f"[{node_name}] Disconnected")

    except Exception as e:
        print(f"[{node_name}] Error: {e}")

def main():
    print("=" * 50)
    print("  PHANTOMMESH SIMULATION")
    print("=" * 50)

    # Create mission
    credentials = create_demo_mission()

    print(f"\n[SIM] Starting {len(credentials)} nodes...")
    print("[SIM] Each node starts with a 2 second delay\n")

    # Start each node in its own thread with staggered delays
    threads = []
    for i, cred in enumerate(credentials):
        t = threading.Thread(
            target=simulate_node,
            args=(cred, credentials, i * 2)
        )
        t.daemon = True
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    print("\n[SIM] Simulation complete")

if __name__ == "__main__":
    main()