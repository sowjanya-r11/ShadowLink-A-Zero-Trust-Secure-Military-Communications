import socket
import requests
import threading
from shadowlink_protocol import create_packet

FLASK_URL = "http://127.0.0.1:5000"
HOST = "127.0.0.1"
PORT = 9000

def listen_for_messages(client):
    """Listens for incoming messages from gateway in background"""
    while True:
        try:
            data = client.recv(4096).decode()
            if not data:
                break
            print(f"\n{'='*40}")
            print(f"  INCOMING: {data}")
            print(f"{'='*40}")
            print("Enter command (msg/broadcast/quit): ", end="", flush=True)
        except:
            break

def main():
    print("=" * 50)
    print("  PHANTOMMESH NODE")
    print("=" * 50)

    # Step 1 — Login
    print("\n[AUTH] Login to PhantomMesh")
    username = input("Username: ")
    password = input("Password: ")

    response = requests.post(f"{FLASK_URL}/auth/login", json={
        "username": username,
        "password": password
    })

    if response.status_code != 200:
        print(f"[ERROR] Login failed: {response.json()['message']}")
        return

    token = response.json()["token"]
    role = response.json()["role"]
    print(f"[AUTH] Login successful — Role: {role}")

    # Step 2 — Node details
    node_name = input("Enter your node name (e.g. ALPHA-01): ").strip().upper()
    mission = input("Enter mission name: ").strip()

    # Step 3 — Connect to gateway
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print(f"\n[NETWORK] Connected to Ghost Gateway")

    # Step 4 — Register with gateway
    reg_message = f"REGISTER|{token}|{node_name}|{mission}"
    client.send(reg_message.encode())

    reg_response = client.recv(4096).decode()
    if reg_response.startswith("ERROR"):
        print(f"[ERROR] Registration failed: {reg_response}")
        client.close()
        return

    print(f"[GATEWAY] {reg_response}")
    print(f"\n[READY] {node_name} is online in mission: {mission}")

    # Step 5 — Start listener thread for incoming messages
    listener = threading.Thread(target=listen_for_messages, args=(client,))
    listener.daemon = True
    listener.start()

    # Step 6 — Command loop
    print("\nCommands:")
    print("  msg       — send message to specific node")
    print("  broadcast — send message to all nodes")
    print("  quit      — disconnect")
    print("-" * 40)

    while True:
        command = input("\nEnter command (msg/broadcast/quit): ").strip().lower()

        if command == "quit":
            print("[EXIT] Disconnecting...")
            client.close()
            break

        elif command == "msg":
            destination = input("Destination node name: ").strip().upper()
            message = input("Mission message: ").strip()
            session_id = username
            packet = create_packet(session_id, message)
            full_packet = f"{token}|{packet}|{destination}"
            client.send(full_packet.encode())

            response = client.recv(4096).decode()
            print(f"[GATEWAY] {response}")

        elif command == "broadcast":
            message = input("Broadcast message: ").strip()
            session_id = username
            packet = create_packet(session_id, message)
            full_packet = f"{token}|{packet}|BROADCAST"
            client.send(full_packet.encode())

            response = client.recv(4096).decode()
            print(f"[GATEWAY] {response}")

        else:
            print("[ERROR] Unknown command — use msg, broadcast or quit")

if __name__ == "__main__":
    main()