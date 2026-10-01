"""
ABBA 2 — ElevenLabs Voiceover Generator
Generates audio voiceover from voiceover JSON using ElevenLabs API.
Voice: Alice (Xb7hH8MSUJpSbSDYk0k2) — Clear, Engaging Educator
Uses free model: eleven_multilingual_v2 (available on free tier)
"""

import json
import os
import time
import requests
from pathlib import Path
from key_manager import KeyRotator

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
ALICE_VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"
# Free model available on ElevenLabs free tier
FREE_MODEL_ID = "eleven_multilingual_v2"

_rotator = KeyRotator("elevenlabs", max_retries=3)


def _tts_request(api_key: str, voice_id: str, text: str, model_id: str) -> bytes:
    """Make a TTS request to ElevenLabs API."""
    url = f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True,
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)

    if resp.status_code == 401:
        raise PermissionError(f"ElevenLabs key invalid (401): {api_key[:20]}...")
    if resp.status_code == 429:
        raise ConnectionError("ElevenLabs rate limited (429)")
    if not resp.ok:
        raise RuntimeError(f"ElevenLabs API error {resp.status_code}: {resp.text[:300]}")

    return resp.content


def generate_voiceover_from_json(
    voiceover_json: list,
    output_dir: str = ".",
) -> list:
    """
    Generate MP3 audio files from voiceover JSON entries.
    Returns list of {section, audio_path} dicts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    audio_files = []
    for i, entry in enumerate(voiceover_json):
        section = entry.get("section", f"section_{i}")
        text = entry.get("text", "")
        voice_id = entry.get("voice_id", ALICE_VOICE_ID)

        if not text.strip():
            print(f"[ElevenLabs] Skipping empty section: {section}")
            continue

        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in section)
        audio_filename = output_path / f"{i:02d}_{safe_name}.mp3"

        print(f"[ElevenLabs] Generating audio for section '{section}' ({len(text)} chars)...")

        def _attempt(api_key):
            return _tts_request(api_key, voice_id, text, FREE_MODEL_ID)

        audio_data = _rotator.call_with_rotation(_attempt)
        audio_filename.write_bytes(audio_data)
        print(f"[ElevenLabs] Saved: {audio_filename}")

        audio_files.append({
            "section": section,
            "timestamp_hint": entry.get("timestamp_hint", 0),
            "audio_path": str(audio_filename),
        })

        # Brief pause to avoid rate limiting
        time.sleep(1)

    return audio_files


def generate_combined_voiceover(voiceover_json: list, output_path: str = "voiceover_combined.mp3") -> str:
    """
    Generate individual audio files and combine them into one MP3.
    Requires ffmpeg to be installed.
    """
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_files = generate_voiceover_from_json(voiceover_json, output_dir=tmpdir)

        if not audio_files:
            raise RuntimeError("No audio files generated!")

        if len(audio_files) == 1:
            import shutil
            shutil.copy(audio_files[0]["audio_path"], output_path)
            return output_path

        # Create ffmpeg concat list
        concat_file = Path(tmpdir) / "concat.txt"
        with open(concat_file, "w") as f:
            for af in sorted(audio_files, key=lambda x: x["timestamp_hint"]):
                f.write(f"file '{af['audio_path']}'\n")

        # Combine with ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "copy",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ElevenLabs] ffmpeg warning: {result.stderr}")
            # Fallback: just use the first audio file
            import shutil
            shutil.copy(audio_files[0]["audio_path"], output_path)

    print(f"[ElevenLabs] Combined voiceover saved: {output_path}")
    return output_path
