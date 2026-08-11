from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fallback_key() -> bytes:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> MultiFernet:
    configured = settings.CONVERSATION_ENCRYPTION_KEYS
    keys = [key.encode("ascii") for key in configured] or [_fallback_key()]
    try:
        return MultiFernet([Fernet(key) for key in keys])
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured("CONVERSATION_ENCRYPTION_KEYS contains an invalid Fernet key.") from exc


def encrypt_message(content: str) -> str:
    return _fernet().encrypt(content.encode("utf-8")).decode("ascii")


def decrypt_message(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return "[This message cannot be decrypted with the configured key.]"
