"""
ABBA 2 — v0.app API Client
Uses v0 Chat REST API (POST /v1/chats + POST /v1/chats/{id}/messages).
Your keys (v1:team_*:vcp_*) are v0 Chat API keys — NOT model-API keys.
Model: v0-1.5-lg (largest, 512k context — best for lesson + code generation)
"""

import json
import time
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from key_manager import KeyRotator

V0_API_BASE = "https://api.v0.dev/v1"
V0_MODEL = "v0-1.5-lg"   # Correct model name. DO NOT use "gpt-5.6-luna".

_rotator = KeyRotator("v0", max_retries=3)


def _create_chat(api_key: str, message: str, system: str = None) -> dict:
    """Create a new v0 chat and return the full response dict."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "message": message,
        "modelConfiguration": {
            "modelId": V0_MODEL,
            "thinking": False,
        },
        "chatPrivacy": "private",
    }
    if system:
        body["system"] = system

    resp = requests.post(
        f"{V0_API_BASE}/chats",
        headers=headers,
        json=body,
        timeout=300,
        stream=True,   # response may be SSE stream
    )

    if resp.status_code == 401:
        raise PermissionError(f"v0 key invalid/unauthorized (401): {api_key[:30]}...")
    if resp.status_code == 403:
        raise PermissionError(f"v0 key forbidden (403) — wrong key type for this endpoint: {api_key[:30]}...")
    if resp.status_code == 429:
        raise ConnectionError("v0.app rate limited (429)")
    if not resp.ok:
        raise RuntimeError(f"v0 API error {resp.status_code}: {resp.text[:500]}")

    return _consume_response(resp)


def _send_message(api_key: str, chat_id: str, message: str) -> dict:
    """Send a follow-up message to an existing chat."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "message": message,
        "modelConfiguration": {
            "modelId": V0_MODEL,
            "thinking": False,
        },
    }
    resp = requests.post(
        f"{V0_API_BASE}/chats/{chat_id}/messages",
        headers=headers,
        json=body,
        timeout=300,
        stream=True,
    )

    if resp.status_code == 401:
        raise PermissionError(f"v0 key invalid (401): {api_key[:30]}...")
    if resp.status_code == 429:
        raise ConnectionError("v0.app rate limited (429)")
    if not resp.ok:
        raise RuntimeError(f"v0 API error {resp.status_code}: {resp.text[:500]}")

    return _consume_response(resp)


def _consume_response(resp) -> dict:
    """
    Consume a v0 API response — handles both:
    - Plain JSON (Content-Type: application/json)
    - SSE stream (Content-Type: text/event-stream)
    Returns a dict with at least {"text": "..."}.
    """
    content_type = resp.headers.get("Content-Type", "")

    # ── Plain JSON ────────────────────────────────────────────────────────
    if "application/json" in content_type:
        data = resp.json()
        # v0 chat API returns: {id, text, files, ...}
        return data

    # ── SSE Stream ───────────────────────────────────────────────────────
    # v0 streams events like:
    #   data: {"type":"chat","id":"...","text":"partial text..."}
    #   data: {"type":"message.experimental_content.chunk","delta":"more text"}
    #   data: [DONE]
    full_text = ""
    last_chat_event = {}

    for raw_line in resp.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line

        if not line.startswith("data:"):
            continue

        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        if event_type == "chat":
            # Full chat object snapshot — grab the latest text
            last_chat_event = event
            if "text" in event:
                full_text = event["text"]

        elif event_type == "message.experimental_content.chunk":
            delta = event.get("delta", "")
            full_text += delta

        elif event_type in ("chat.title", "chat.name"):
            pass  # title updates — not needed

        elif "error" in event:
            raise RuntimeError(f"v0 stream error: {event['error']}")

    # Merge streamed text back into the last known chat snapshot
    result = last_chat_event if last_chat_event else {}
    if full_text:
        result["text"] = full_text

    return result


def call_v0(
    system_prompt: str,
    user_message: str,
    attachment_text: str = None,
    attachment_name: str = "attachment.txt",
) -> str:
    """
    Create a v0 chat with optional text file attachment embedded in the message.
    Rotates keys on failure. Returns the AI text response.
    """
    # Embed attachment as part of the message text (v0 Chat API doesn't
    # accept raw file uploads — embed content inline)
    if attachment_text:
        user_message = (
            f"{user_message}\n\n"
            f"--- ATTACHED FILE: {attachment_name} ---\n"
            f"{attachment_text}\n"
            f"--- END OF {attachment_name} ---"
        )

    def _attempt(api_key):
        data = _create_chat(api_key, user_message, system=system_prompt)
        text = data.get("text", "")
        if not text:
            print(f"[v0] WARNING: empty text in response. Full response keys: {list(data.keys())}")
            # Sometimes text is nested under files[0].source or similar
            files = data.get("files", [])
            if files:
                text = files[0].get("source", "")
        if not text:
            raise RuntimeError(f"v0 returned empty text. Response: {str(data)[:300]}")
        return text

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
    )
    print(f"[v0] Lesson response received ({len(response)} chars)")
    return response


def generate_code(code_gen_prompt_with_lesson: str) -> str:
    """Action 2: Generate Manim Python code from lesson."""
    print("[v0] Generating Manim code...")
    response = call_v0(
        system_prompt=(
            "You are an expert Manim (Mathematical Animation Engine) developer. "
            "Return only Python code inside ====CODE START==== ... ====CODE END==== delimiters."
        ),
        user_message=code_gen_prompt_with_lesson,
    )
    print(f"[v0] Code response received ({len(response)} chars)")
    return response
