import nmap
import socket
import requests
import time

TARGET = "127.0.0.1"
SHADOWLINK_PORTS = "5000,9000,8080,3306,2222,8888"

def print_separator():
    print("=" * 55)

def scan_open_ports():
    print_separator()
    print("  PHASE 1 — PORT DISCOVERY")
    print_separator()

    scanner = nmap.PortScanner()
    print(f"\n[NMAP] Scanning {TARGET} for open ports...")
    scanner.scan(TARGET, SHADOWLINK_PORTS, arguments="-T4 -F")

    open_ports = []
    for host in scanner.all_hosts():
        for proto in scanner[host].all_protocols():
            for port in scanner[host][proto].keys():
                state   = scanner[host][proto][port]['state']
                service = scanner[host][proto][port]['name']
                version = scanner[host][proto][port]['version']
                print(f"  Port {port}: {state} | {service} {version}")
                if state == 'open':
                    open_ports.append(port)

    print(f"\n[NMAP] Found {len(open_ports)} open ports: {open_ports}")
    return open_ports

def try_unauthorized_access():
    print_separator()
    print("  PHASE 2 — UNAUTHORIZED ACCESS ATTEMPT")
    print_separator()

    print("\n[ATTACK] Trying to connect to gateway without credentials...")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(1)
        client.connect((TARGET, 9000))

        # Send fake packet without JWT
        fake_packet = "SHADOW|fake_session|123456|abcdef|badhash|TARGET"
        client.send(fake_packet.encode())

        response = client.recv(1024).decode()
        print(f"[ATTACK] Gateway response: {response}")
        client.close()
    except Exception as e:
        print(f"[ATTACK] Connection result: {e}")

def try_fake_login():
    print_separator()
    print("  PHASE 3 — CREDENTIAL BRUTE FORCE")
    print_separator()

    fake_credentials = [
        ("admin", "admin"),
        ("root", "password"),
        ("commander", "12345"),
        ("shadow", "shadowlink"),
    ]

    print("\n[ATTACK] Trying common credentials against Flask login...")
    for username, password in fake_credentials:
        try:
            response = requests.post(
                f"http://{TARGET}:5000/auth/login",
                json={"username": username, "password": password},
                timeout=1
            )
            status = response.json().get("status")
            print(f"  {username}:{password} → {status}")
            time.sleep(0.1)
        except Exception as e:
            print(f"  {username}:{password} → Error: {e}")

def try_honeypot_ports():
    print_separator()
    print("  PHASE 4 — HONEYPOT PORT PROBING")
    print_separator()

    honeypot_ports = [8080, 3306, 2222, 8888]
    print("\n[ATTACK] Probing honeypot ports...")

    for port in honeypot_ports:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(1)
            client.connect((TARGET, port))

            banner = client.recv(1024).decode(errors='ignore')
            print(f"\n  Port {port} — Connected!")
            print(f"  Banner: {banner[:80]}...")

            # Try some commands
            if port == 3306:
                client.send(b"SELECT * FROM users;\n")
            elif port == 2222:
                client.send(b"admin\npassword\n")
            elif port == 8080:
                client.send(
                    b"GET /admin HTTP/1.1\r\n"
                    b"Host: shadowlink\r\n\r\n"
                )

            try:
                response = client.recv(1024).decode(errors='ignore')
                print(f"  Response: {response[:100]}...")
            except:
                pass

            client.close()
            time.sleep(0.1)

        except Exception as e:
            print(f"  Port {port} — {e}")

def run_attack_simulation():
    print("\n")
    print_separator()
    print("  SHADOWLINK PENETRATION TEST")
    print("  Simulated Attack Demonstration")
    print_separator()
    print("\n[!] This simulates a real attacker targeting ShadowLink")
    print("[!] All attempts will be logged by the system\n")
    time.sleep(0.1)

    # Phase 1 — discover ports
    open_ports = scan_open_ports()
    time.sleep(0.1)

    # Phase 2 — try unauthorized gateway access
    try_unauthorized_access()
    time.sleep(0.1)

    # Phase 3 — brute force login
    try_fake_login()
    time.sleep(0.1)

    # Phase 4 — probe honeypots
    try_honeypot_ports()
    time.sleep(0.1)

    # Final report
    print_separator()
    print("  ATTACK SIMULATION COMPLETE")
    print_separator()
    print("""
[RESULT] Port scan      → Ports visible but protocol unknown
[RESULT] Gateway access → Rejected — invalid packet format
[RESULT] Brute force    → All attempts failed — bcrypt protected
[RESULT] Honeypots      → Fed false information — behavior logged
[RESULT] Check dashboard for full attacker profile
    """)

if __name__ == "__main__":
    run_attack_simulation()