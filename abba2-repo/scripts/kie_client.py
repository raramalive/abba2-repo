"""
ABBA 2 — Kie.ai API Client
Uses Kie.ai's Gemini Flash 3.8 endpoint to analyze videos and polish Manim code.
Endpoint: https://api.kie.ai/gemini/v1/models/gemini-3-8-flash:generateContent
"""

import base64
import json
import time
import requests
from pathlib import Path
from key_manager import KeyRotator

KIE_API_BASE = "https://api.kie.ai/gemini/v1"
KIE_MODEL = "gemini-3-8-flash"

_rotator = KeyRotator("kie", max_retries=3)


def _encode_video_base64(video_path: str) -> str:
    """Encode video file as base64."""
    with open(video_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _gemini_request(api_key: str, contents: list, generation_config: dict = None) -> str:
    """Make a single request to Kie.ai Gemini endpoint."""
    url = f"{KIE_API_BASE}/models/{KIE_MODEL}:generateContent"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "contents": contents,
        "generationConfig": generation_config or {
            "maxOutputTokens": 8192,
            "temperature": 0.3,
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=600)

    if resp.status_code == 401:
        raise PermissionError(f"Kie.ai key invalid (401): {api_key[:20]}...")
    if resp.status_code == 429:
        raise ConnectionError("Kie.ai rate limited (429)")
    if not resp.ok:
        raise RuntimeError(f"Kie.ai API error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    # Extract text from Gemini response format
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Kie.ai returned no candidates: {data}")

    text_parts = []
    for candidate in candidates:
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])

    return "\n".join(text_parts)


def polish_code_with_video(
    polish_prompt: str,
    video_path: str,
    unpolished_code: str,
) -> str:
    """
    Action 3: Send the polisher prompt + video + code to Kie.ai Gemini.
    Returns the full response containing polished code + voiceover JSON.
    """
    print(f"[Kie] Encoding video: {video_path}")
    video_b64 = _encode_video_base64(video_path)

    # Determine video MIME type
    video_ext = Path(video_path).suffix.lower()
    mime_map = {".mp4": "video/mp4", ".mov": "video/quicktime", ".avi": "video/x-msvideo"}
    video_mime = mime_map.get(video_ext, "video/mp4")

    # Replace placeholder in prompt with actual code
    final_prompt = polish_prompt.replace("{{code_here}}", unpolished_code)

    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "inlineData": {
                        "mimeType": video_mime,
                        "data": video_b64,
                    }
                },
                {
                    "text": final_prompt,
                },
            ],
        }
    ]

    print("[Kie] Sending video + code to Gemini Flash 3.8 for polishing...")

    def _attempt(api_key):
        return _gemini_request(api_key, contents)

    result = _rotator.call_with_rotation(_attempt)
    print(f"[Kie] Polish response received ({len(result)} chars)")
    return result
