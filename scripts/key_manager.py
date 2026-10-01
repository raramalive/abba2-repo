"""
ABBA 2 — API Key Rotation Manager
Loads API keys from secrets JSON files and rotates through them on failure.
"""

import json
import os
import time
import random
from pathlib import Path

# Resolve secrets dir relative to THIS file — works regardless of cwd
_THIS_DIR = Path(__file__).resolve().parent
SECRETS_DIR = _THIS_DIR.parent / "secrets"


def load_keys(service: str) -> list:
    """Load API keys for a given service from secrets JSON."""
    key_file = SECRETS_DIR / f"{service}_api_keys.json"
    if not key_file.exists():
        raise FileNotFoundError(
            f"Key file not found: {key_file}\n"
            f"SECRETS_DIR resolved to: {SECRETS_DIR}\n"
            f"Files there: {list(SECRETS_DIR.iterdir()) if SECRETS_DIR.exists() else 'DIR MISSING'}"
        )
    with open(key_file) as f:
        data = json.load(f)
    keys = data.get("keys", [])
    if not keys:
        raise ValueError(f"No keys found in {key_file}")
    print(f"[KeyManager] Loaded {len(keys)} key(s) for service '{service}'")
    return keys


class KeyRotator:
    """Rotates through API keys and retries on failure."""

    def __init__(self, service: str, max_retries: int = 3):
        self.service = service
        self.keys = load_keys(service)
        self.max_retries = max_retries
        self._index = 0

    def current_key(self) -> str:
        return self.keys[self._index % len(self.keys)]

    def next_key(self) -> str:
        self._index = (self._index + 1) % len(self.keys)
        print(f"[KeyRotator] Rotating {self.service} key → index {self._index}")
        return self.current_key()

    def call_with_rotation(self, fn, *args, **kwargs):
        """
        Call fn(api_key, *args, **kwargs).
        On any exception, rotate key and retry with exponential backoff.
        """
        last_error = None
        total_attempts = self.max_retries * len(self.keys)
        for attempt in range(total_attempts):
            key = self.current_key()
            try:
                result = fn(key, *args, **kwargs)
                return result
            except PermissionError as e:
                # 401/403 — rotate immediately, no long backoff
                last_error = e
                print(f"[KeyRotator] Auth error on attempt {attempt+1}: {e}")
                self.next_key()
                time.sleep(1)
            except Exception as e:
                last_error = e
                print(f"[KeyRotator] Attempt {attempt+1}/{total_attempts} failed: {e}")
                self.next_key()
                backoff = min(2 ** (attempt % 5), 30)
                print(f"[KeyRotator] Sleeping {backoff}s before retry...")
                time.sleep(backoff)

        raise RuntimeError(
            f"All {self.service} keys exhausted after {total_attempts} attempts. "
            f"Last error: {last_error}"
        )


def get_v0_key() -> str:
    return random.choice(load_keys("v0"))


def get_kie_key() -> str:
    return random.choice(load_keys("kie"))


def get_elevenlabs_key() -> str:
    return random.choice(load_keys("elevenlabs"))
