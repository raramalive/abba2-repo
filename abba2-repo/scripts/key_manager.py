"""
ABBA 2 — API Key Rotation Manager
Loads API keys from secrets JSON files and rotates through them on failure.
"""

import json
import os
import time
import random
from pathlib import Path

SECRETS_DIR = Path(__file__).parent.parent / "secrets"


def load_keys(service: str) -> list:
    """Load API keys for a given service from secrets JSON."""
    key_file = SECRETS_DIR / f"{service}_api_keys.json"
    if not key_file.exists():
        raise FileNotFoundError(f"Key file not found: {key_file}")
    with open(key_file) as f:
        data = json.load(f)
    return data["keys"]


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
        On exception or non-2xx, rotate key and retry.
        """
        last_error = None
        for attempt in range(self.max_retries * len(self.keys)):
            key = self.current_key()
            try:
                result = fn(key, *args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                print(f"[KeyRotator] Attempt {attempt+1} failed with key index {self._index}: {e}")
                self.next_key()
                time.sleep(2 ** (attempt % 4))  # exponential backoff, reset per rotation cycle
        raise RuntimeError(
            f"All {self.service} keys exhausted after {attempt+1} attempts. Last error: {last_error}"
        )


def get_v0_key() -> str:
    keys = load_keys("v0")
    return random.choice(keys)


def get_kie_key() -> str:
    keys = load_keys("kie")
    return random.choice(keys)


def get_elevenlabs_key() -> str:
    keys = load_keys("elevenlabs")
    return random.choice(keys)
