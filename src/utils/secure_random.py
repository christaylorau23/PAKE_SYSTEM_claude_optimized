#!/usr/bin/env python3
"""Secure Random Utilities for PAKE System
Provides cryptographically secure random number generation.
"""

import secrets
import string
from typing import Any, List, Union


def secure_random_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Generate a cryptographically secure random float."""
    if min_val >= max_val:
        msg = "min_val must be less than max_val"
        raise ValueError(msg)

    range_size = max_val - min_val
    # Use a large range for better precision
    random_int = secrets.randbelow(2**32)
    return (random_int / (2**32)) * range_size + min_val


def secure_random_int(min_val: int, max_val: int) -> int:
    """Generate a cryptographically secure random integer."""
    if min_val >= max_val:
        msg = "min_val must be less than max_val"
        raise ValueError(msg)

    return secrets.randbelow(max_val - min_val + 1) + min_val


def secure_random_string(length: int = 32, alphabet: str = None) -> str:
    """Generate a cryptographically secure random string."""
    if alphabet is None:
        alphabet = string.ascii_letters + string.digits

    return "".join(secrets.choice(alphabet) for _ in range(length))


def secure_shuffle(items: list[Any]) -> list[Any]:
    """Shuffle a list using cryptographically secure random."""
    # Create a copy to avoid modifying the original
    shuffled = items.copy()
    secrets.shuffle(shuffled)
    return shuffled


def secure_choice(items: list[Any]) -> Any:
    """Choose a random item from a list using cryptographically secure random."""
    return secrets.choice(items)


def secure_token_bytes(length: int = 32) -> bytes:
    """Generate cryptographically secure random bytes."""
    return secrets.token_bytes(length)


def secure_token_hex(length: int = 32) -> str:
    """Generate cryptographically secure random hex string."""
    return secrets.token_hex(length)


def secure_token_urlsafe(length: int = 32) -> str:
    """Generate cryptographically secure random URL-safe string."""
    return secrets.token_urlsafe(length)
