import time
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

PROTOCOL_NAME = "SHADOW"
DEFAULT_KEY = b'shadowlinkkey000'  # 16 bytes, fallback only

def generate_session_key():
    """Generate a unique 16 byte AES key for a mission session"""
    return get_random_bytes(16)

def encrypt_payload(message, session_key=None):
    key = session_key if session_key else DEFAULT_KEY
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(message.encode(), AES.block_size))
    return (iv + encrypted).hex()

def decrypt_payload(encrypted_hex, session_key=None):
    key = session_key if session_key else DEFAULT_KEY
    raw = bytes.fromhex(encrypted_hex)
    iv = raw[:16]
    encrypted = raw[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    from Crypto.Util.Padding import unpad
    decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
    return decrypted.decode()

def create_packet(session_id, message, session_key=None):
    protocol = PROTOCOL_NAME
    timestamp = str(int(time.time()))
    encrypted_payload = encrypt_payload(message, session_key)
    hash_input = protocol + session_id + timestamp + encrypted_payload
    packet_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    # Format: SHADOW|session|timestamp|payload|hash
    packet = f"{protocol}|{session_id}|{timestamp}|{encrypted_payload}|{packet_hash}"
    return packet

def verify_packet(packet_str):
    """Verify packet integrity — returns True if valid"""
    parts = packet_str.split("|")
    if len(parts) != 5:
        return False
    protocol, session, timestamp, payload, received_hash = parts
    hash_input = protocol + session + timestamp + payload
    computed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    return computed_hash == received_hash