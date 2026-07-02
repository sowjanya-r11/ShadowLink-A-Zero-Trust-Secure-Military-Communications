from scapy.all import sniff, IP, TCP
from collections import defaultdict
import time
import sqlite3
import threading

PORT = 9000
connection_attempts = defaultdict(list)
SYN_THRESHOLD = 10
lock = threading.Lock()

def log_scapy_alert(src_ip, alert_type, details):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deception_logs
            (attacker_ip, port_accessed, attempt_type,
             data_sent, fake_response)
            VALUES (?, ?, ?, ?, ?)
        """, (src_ip, PORT, alert_type, details, "SCAPY ALERT"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SCAPY] Log error: {e}")

def packet_callback(packet):
    if IP not in packet or TCP not in packet:
        return

    src  = packet[IP].src
    dst  = packet[IP].dst
    sport = packet[TCP].sport
    dport = packet[TCP].dport
    flags = packet[TCP].flags

    # Show every packet hitting ShadowLink ports
    if dport in [9000, 5000, 8080, 3306, 2222, 8888]:
        print(f"[SCAPY] {src}:{sport} → {dst}:{dport} | FLAGS: {flags}")

    # SYN flood detection
    if flags == 'S' and dport == PORT:
        with lock:
            now = time.time()
            connection_attempts[src].append(now)

            # Keep only last 5 seconds
            connection_attempts[src] = [
                t for t in connection_attempts[src]
                if now - t < 5
            ]

            count = len(connection_attempts[src])

            if count > SYN_THRESHOLD:
                print(f"\n[SCAPY] ⚠ SYN FLOOD DETECTED")
                print(f"[SCAPY] Source: {src}")
                print(f"[SCAPY] {count} SYN packets in 5 seconds\n")
                log_scapy_alert(
                    src,
                    "syn_flood",
                    f"{count} SYN packets in 5 seconds"
                )

    # Port scan detection — RST packets
    if flags == 'R':
        print(f"[SCAPY] Port scan RST detected from {src}")
        log_scapy_alert(
            src,
            "port_scan_rst",
            f"RST from {src}:{sport} to {dport}"
        )

    # NULL packet detection
    if flags == 0:
        print(f"[SCAPY] NULL packet detected from {src}")
        log_scapy_alert(
            src,
            "null_packet",
            f"NULL flags from {src}"
        )

def start_sniffer():
    print("=" * 50)
    print("  SHADOWLINK NETWORK SNIFFER")
    print("  Raw Packet Level Monitor")
    print("=" * 50)
    print(f"\n[SCAPY] Monitoring all ShadowLink ports...")
    print(f"[SCAPY] SYN flood threshold: {SYN_THRESHOLD} packets/5s")
    print(f"[SCAPY] Watching ports: 9000, 5000, 8080, 3306, 2222\n")

    sniff(
        filter="tcp",
        prn=packet_callback,
        store=False,
        iface="lo"        # lo = loopback interface for 127.0.0.1
    )

if __name__ == "__main__":
    start_sniffer()