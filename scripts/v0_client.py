"""
ABBA 2 — v0.app API Client
Communicates with v0.app chat completions API using GPT-5.6-Luna model.
Supports file attachments and API key rotation.
"""

import json
import time
import requests
from pathlib import Path
from key_manager import KeyRotator

V0_API_BASE = "https://api.v0.dev/v1"
V0_MODEL = "gpt-5.6-luna"  # As specified

_rotator = KeyRotator("v0", max_retries=3)


def _chat_request(api_key: str, messages: list, max_tokens: int = 8192) -> str:
    """Make a single chat request to v0.app API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": V0_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = requests.post(
        f"{V0_API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=300,
    )
    if resp.status_code == 401:
        raise PermissionError(f"v0.app API key invalid (401): {api_key[:20]}...")
    if resp.status_code == 429:
        raise ConnectionError(f"v0.app rate limited (429)")
    if not resp.ok:
        raise RuntimeError(f"v0.app API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    # Extract text from response
    content = data["choices"][0]["message"]["content"]
    return content


def call_v0(
    system_prompt: str,
    user_message: str,
    attachment_text: str = None,
    attachment_name: str = "attachment.txt",
    max_tokens: int = 8192,
) -> str:
    """
    Call v0.app with optional text file attachment.
    Rotates keys on failure.
    """
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    user_content = user_message
    if attachment_text:
        user_content = (
            f"{user_message}\n\n"
            f"--- ATTACHED FILE: {attachment_name} ---\n"
            f"{attachment_text}\n"
            f"--- END OF {attachment_name} ---"
        )

    messages.append({"role": "user", "content": user_content})

    def _attempt(api_key):
        return _chat_request(api_key, messages, max_tokens)

    result = _rotator.call_with_rotation(_attempt)
    return result


def generate_lesson(master_prompt: str, former_lessons_content: str) -> str:
    """Action 1: Generate a new lesson using master prompt + former lessons."""
    print("[v0] Generating lesson with master prompt...")
    response = call_v0(
        system_prompt="You are ABBA, an elite AI-powered mathematics and science educator.",
        user_message=master_prompt,
        attachment_text=former_lessons_content,
        attachment_name="former_lessons.txt",
        max_tokens=8192,
    )
    print(f"[v0] Lesson response received ({len(response)} chars)")
    return response


def generate_code(code_gen_prompt_with_lesson: str) -> str:
    """Action 2: Generate Manim Python code from lesson."""
    print("[v0] Generating Manim code...")
    response = call_v0(
        system_prompt="You are an expert Manim developer. Return only code inside the specified delimiters.",
        user_message=code_gen_prompt_with_lesson,
        max_tokens=8192,
    )
    print(f"[v0] Code response received ({len(response)} chars)")
    return response
