"""Fernet-based API-key encryption.

Keys live encrypted at rest; plaintext is kept in memory only for the minimum
duration required to sign exchange calls.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from ..config import settings


def _derive_key(master: str) -> bytes:
    if not master:
        raise ValueError("MASTER_KEY not set. Run: openssl rand -base64 32")
    digest = hashlib.sha256(master.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def get_cipher() -> Fernet:
    return Fernet(_derive_key(settings.master_key))


def encrypt(plaintext: str) -> str:
    return get_cipher().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return get_cipher().decrypt(ciphertext.encode()).decode()
