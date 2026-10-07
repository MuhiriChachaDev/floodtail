"""AES-GCM for PII at rest + irreversible hash_token for identifiers."""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BytesLike = Union[str, bytes]


def _key_from_base64(aes_key_base64: str) -> bytes:
    raw = base64.b64decode(aes_key_base64)
    if len(raw) not in (16, 24, 32):
        # Derive a 32-byte key if mis-sized (prototype convenience)
        raw = hashlib.sha256(raw).digest()
    return raw


def hash_token(value: BytesLike, *, salt: str = "floodtail") -> str:
    """Irreversible SHA-256 token (first 32 hex chars) for PII identifiers."""
    if isinstance(value, bytes):
        data = value
    else:
        data = str(value).encode("utf-8")
    digest = hashlib.sha256(salt.encode("utf-8") + b"|" + data).hexdigest()
    return digest[:32]


def encrypt_aes_gcm(plaintext: BytesLike, aes_key_base64: str) -> str:
    """
    Encrypt UTF-8 plaintext with AES-GCM.
    Returns base64(nonce || ciphertext||tag).
    """
    key = _key_from_base64(aes_key_base64)
    if isinstance(plaintext, str):
        data = plaintext.encode("utf-8")
    else:
        data = plaintext
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, data, None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_aes_gcm(token_b64: str, aes_key_base64: str) -> str:
    """Decrypt AES-GCM payload produced by encrypt_aes_gcm."""
    key = _key_from_base64(aes_key_base64)
    blob = base64.b64decode(token_b64)
    nonce, ct = blob[:12], blob[12:]
    pt = AESGCM(key).decrypt(nonce, ct, None)
    return pt.decode("utf-8")


def encrypt_optional(value: Optional[str], aes_key_base64: str) -> Optional[str]:
    if value is None or value == "":
        return value
    return encrypt_aes_gcm(value, aes_key_base64)
