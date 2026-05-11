# Encryption service for FlatWatch (POC - AES-256)
import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

from .config import ENCRYPTION_KEY_TEXT


# POC: In production, use proper key management (KMS, HashiCorp Vault, etc.)
# Key should be 256 bits (32 bytes) for AES-256
ENCRYPTION_KEY = ENCRYPTION_KEY_TEXT.encode()[:32]  # Ensure exactly 32 bytes


def encrypt_data(plaintext: str) -> str:
    """
    Encrypt data using AES-256-GCM.

    Returns base64-encoded nonce + ciphertext.
    """
    if not plaintext:
        return ""

    aesgcm = AESGCM(ENCRYPTION_KEY)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

    # Return nonce + ciphertext as base64
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_data(encrypted: str) -> str:
    """
    Decrypt AES-256-GCM encrypted data.
    """
    if not encrypted:
        return ""

    try:
        data = base64.b64decode(encrypted.encode())
        nonce = data[:12]
        ciphertext = data[12:]

        aesgcm = AESGCM(ENCRYPTION_KEY)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()
    except Exception:
        # Return original if decryption fails
        return encrypted


def encrypt_email(email: str) -> str:
    """Encrypt user email."""
    return encrypt_data(email)


def decrypt_email(encrypted_email: str) -> str:
    """Decrypt user email."""
    return decrypt_data(encrypted_email)


def encrypt_amount(amount: float) -> str:
    """Encrypt transaction amount."""
    return encrypt_data(str(amount))


def decrypt_amount(encrypted_amount: str) -> float:
    """Decrypt transaction amount."""
    decrypted = decrypt_data(encrypted_amount)
    try:
        return float(decrypted)
    except ValueError:
        return 0.0


def hash_sensitive_data(data: str) -> str:
    """
    Create hash for sensitive data (for verification without decryption).
    Uses SHA-256.
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()
