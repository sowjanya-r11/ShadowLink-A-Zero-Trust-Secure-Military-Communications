# ShadowLink: A Zero-Trust Secure Military Communications Network

ShadowLink is a zero-trust secure military communications network built entirely from scratch in Python. It implements a custom packet protocol, AES-CBC encryption, SHA-256 integrity verification, JWT session management, and bcrypt password hashing across **12 independent security layers**. Beyond passive defense, it features an active cyber deception engine that deploys honeypots and behavioral fingerprinting to mislead and profile attackers, alongside a real-time Flask-based command dashboard for mission control and threat intelligence.

---

## Core Features

- **Zero Trust Verification** — every packet must independently prove identity, integrity, and freshness before being accepted
- **Custom ShadowLink Protocol** — pipe-delimited packet format with dedicated fields for token, session, timestamp, payload, hash, and destination
- **AES-CBC Encryption** — per-mission session keys with random IVs to prevent pattern analysis
- **JWT + bcrypt Authentication** — signed session tokens and slow password hashing to resist spoofing and brute force
- **Adaptive Trust Score Firewall** — dynamically scores nodes and permanently blocks those that fall below a trust threshold
- **Active Deception Engine** — simulated Apache, MySQL, OpenSSH, and FTP honeypots that mislead attackers while logging their behavior
- **Behavioral Fingerprinting** — classifies attackers into five profiles (Probe, Reconnaissance, Port Scanner, Brute Force, Credential Stuffer)
- **Real-Time Command Dashboard** — Flask-based UI with live node status, mission management, threat level indicators, and deception logs
- **Self-Destructing Missions** — all credentials and session keys are permanently deleted when a mission closes, leaving zero trace

---

## System Architecture

ShadowLink uses a centralized Gateway-Node architecture, split into three functional planes:

- **Management Plane** — Flask-based Command Dashboard for mission control and threat intelligence
- **Operations Plane** — authenticated soldier nodes communicating via the custom ShadowLink protocol
- **Defence Plane** — Scapy-driven packet sniffer, active deception engine (honeypots), and adaptive trust-score firewall

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.11 |
| Encryption | AES-256 CBC, SHA-256, bcrypt |
| Auth | PyJWT |
| Networking | Scapy, Nmap |
| Web/UI | Flask, HTML |
| Storage | SQLite |

---

## Project Structure

```
ShadowLink/
├── templates/
│   ├── dashboard.html
│   ├── login.html
│   └── soldier_dashboard.html
├── app.py                   # Flask command dashboard
├── auth.py                  # Authentication (bcrypt, JWT)
├── client.py                # Soldier node client
├── database.py              # SQLite database logic
├── gateway.py                # Central gateway server
├── honeypot.py               # Deception engine
├── network_scan.py           # Network reconnaissance detection
├── node.py                   # Node representation/logic
├── replay_test.py            # Replay attack test script
├── server_socket.py          # Core socket server
├── shadowlink_protocol.py    # Custom packet protocol
├── sniffer.py                # Scapy raw packet monitoring
├── stimulate.py               # Simulation/testing utilities
├── tamper_test.py             # Packet tampering test script
└── requirements.txt
```

---

## Security Layers

| # | Mechanism | Defends Against |
|---|---|---|
| 1 | bcrypt password hashing | Credential theft, brute force |
| 2 | JWT session tokens | Identity spoofing, session hijacking |
| 3 | Custom ShadowLink Protocol | Protocol fingerprinting, automated attacks |
| 4 | AES-CBC encryption | Packet interception, traffic analysis |
| 5 | Per-mission session keys | Key compromise, cross-mission attacks |
| 6 | SHA-256 integrity hash | Packet tampering, man-in-the-middle |
| 7 | Timestamp replay protection | Replay attacks, packet reuse |
| 8 | Adaptive trust score firewall | Brute force, repeated attacks |
| 9 | Credential self-destruction | Post-mission credential theft |
| 10 | Honeypot deception engine | Reconnaissance, port scanning |
| 11 | Behavioral fingerprinting | Advanced persistent threats |
| 12 | Scapy raw packet monitoring | Network-layer attacks, SYN floods |

---

## Getting Started

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
git clone https://github.com/<your-username>/ShadowLink.git
cd ShadowLink
pip install -r requirements.txt
```

### Running

```bash
# Start the gateway server
python gateway.py

# Start the command dashboard
python app.py
```

Then open `http://127.0.0.1:5000/dashboard` in your browser.

---

## Validation

ShadowLink was tested with a 4-phase penetration test using Nmap and custom scripts, covering discovery (Scapy monitoring), reconnaissance (honeypots), integrity (SHA-256 tamper detection), and persistence (replay protection). The system neutralized unauthorized attempts across all tested vectors while maintaining uptime under simulated SYN flood and brute-force conditions.

---

## Limitations

- Centralized gateway is a single point of failure
- Secrets are currently hardcoded rather than managed via environment variables/vault
- No mutual authentication (gateway identity isn't cryptographically verified to nodes)
- No message persistence for offline nodes
- Trust scores are stored in memory and reset on gateway restart

## Future Work

- Mutual TLS (mTLS) for two-way certificate-based verification
- Perfect Forward Secrecy via ephemeral Diffie-Hellman key exchange
- Decentralized mesh architecture
- ML-based anomaly detection for APT patterns
- Cryptographic non-repudiation via digital signatures
- Canary tokens for honey-data exfiltration alerts

---
