from __future__ import annotations

from typing import Tuple

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Argon2id parameters tuned for backend API login usage.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, stored_password: str) -> Tuple[bool, bool]:
    """
    Returns (is_valid, needs_upgrade).
    - needs_upgrade=True when hash params need rehash, or stored value is legacy plaintext.
    """
    stored = (stored_password or "").strip()
    if not stored:
        return False, False

    # Legacy plaintext fallback: allow one-time upgrade on successful login.
    if not stored.startswith("$argon2"):
        return plain_password == stored, plain_password == stored

    try:
        ok = _hasher.verify(stored, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False, False

    needs_upgrade = _hasher.check_needs_rehash(stored)
    return ok, needs_upgrade
