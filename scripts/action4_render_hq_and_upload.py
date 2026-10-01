"""
ABBA 2 — Action 4: High Quality Render & Upload to Google Drive
1. Renders the perfect Manim code at high quality (-qh)
2. Generates voiceover audio via ElevenLabs
3. Uploads video, audio, code, and voiceover JSON to Google Drive "JESUS" folder
4. Archives lesson to former_lessons.txt and clears all state files
Only runs if current_perfect_code.py is NOT empty.
"""

import sys
import os
import subprocess
import shutil
import json
from pathlib import Path
import datetime
import re

sys.path.insert(0, os.path.dirname(__file__))

from state_manager import (
    is_perfect_code_empty,
    read_current_perfect_code,
    read_current_voiceover,
    read_current_lesson,
    archive_current_lesson,
    clear_current_unpolished_code,
    clear_current_perfect_code,
    clear_current_voiceover,
)
from gdrive_uploader import upload_to_jesus_folder
from elevenlabs_client import generate_voiceover_from_json

RENDER_DIR = Path("/tmp/manim_render_hq")
SCENE_FILE = RENDER_DIR / "scene.py"
ASSETS_DIR = RENDER_DIR / "assets"


def render_high_quality(python_code: str) -> str:
    """Render Manim scene at high quality (-qh) and return path to output video."""
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    SCENE_FILE.write_text(python_code, encoding="utf-8")
    print(f"[Action 4] Scene file written to {SCENE_FILE}")

    # Detect scene class name
    match = re.search(r"class\s+(\w+)\s*\(.*Scene.*\)", python_code)
    scene_class = match.group(1) if match else "MainScene"
    print(f"[Action 4] Detected scene class: {scene_class}")

    cmd = [
        "manim",
        "-qh",              # HIGH quality
        "--media_dir", str(RENDER_DIR / "media"),
        str(SCENE_FILE),
        scene_class,
    ]
    print(f"[Action 4] Running HIGH quality render: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3000)

    print("[Action 4] STDOUT:", result.stdout[-3000:] if result.stdout else "(none)")
    if result.returncode != 0:
        print("[Action 4] STDERR:", result.stderr[-2000:])
        raise RuntimeError(f"High quality Manim render failed (exit {result.returncode})")

    # Find output video
    media_dir = RENDER_DIR / "media"
    video_files = list(media_dir.rglob("*.mp4"))
    if not video_files:
        video_files = list(media_dir.rglob("*.mov"))
    if not video_files:
        raise RuntimeError(f"No video output found in {media_dir}")

    video_path = max(video_files, key=lambda p: p.stat().st_mtime)
    print(f"[Action 4] High quality video: {video_path}")

    # Copy to assets dir with timestamp name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"ABBA2_lesson_{timestamp}.mp4"
    output_video = ASSETS_DIR / output_name
    shutil.copy(video_path, output_video)
    return str(output_video)


def main():
    print("=" * 60)
    print("ABBA 2 — Action 4: High Quality Render & Upload")
    print("=" * 60)

    if is_perfect_code_empty():
        print("[Action 4] current_perfect_code.py is EMPTY. Nothing to render.")
        print("[Action 4] Run Action 3 first.")
        sys.exit(0)

    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load perfect code
    perfect_code = read_current_perfect_code()
    print(f"[Action 4] Perfect code loaded ({len(perfect_code)} chars)")

    # Load voiceover JSON
    voiceover_data = read_current_voiceover()
    print(f"[Action 4] Voiceover data loaded ({len(voiceover_data)} sections)")

    # Load current lesson (for archiving after)
    current_lesson = read_current_lesson()

    # --- Step 1: Render high quality video ---
    print("[Action 4] Rendering high quality video...")
    try:
        video_path = render_high_quality(perfect_code)
        print(f"[Action 4] ✅ Video rendered: {video_path}")
    except Exception as e:
        print(f"[Action 4] ERROR: High quality render failed: {e}")
        sys.exit(1)

    # --- Step 2: Generate voiceover audio ---
    audio_path = None
    if voiceover_data:
        print("[Action 4] Generating voiceover via ElevenLabs...")
        try:
            audio_files = generate_voiceover_from_json(
                voiceover_data,
                output_dir=str(ASSETS_DIR / "audio"),
            )
            if audio_files:
                # If ffmpeg available, combine; otherwise upload individual files
                try:
                    from elevenlabs_client import generate_combined_voiceover
                    combined_audio = str(ASSETS_DIR / f"voiceover_{timestamp}.mp3")
                    generate_combined_voiceover(voiceover_data, combined_audio)
                    audio_path = combined_audio
                except Exception as combine_err:
                    print(f"[Action 4] Could not combine audio: {combine_err}")
                    audio_path = audio_files[0]["audio_path"]
            print(f"[Action 4] ✅ Voiceover generated: {audio_path}")
        except Exception as e:
            print(f"[Action 4] WARNING: Voiceover generation failed: {e}")
            print("[Action 4] Continuing without audio...")
    else:
        print("[Action 4] No voiceover data — skipping audio generation.")

    # --- Step 3: Save supporting files ---
    # Save perfect code file
    code_file = ASSETS_DIR / f"scene_perfect_{timestamp}.py"
    code_file.write_text(perfect_code, encoding="utf-8")

    # Save voiceover JSON
    voiceover_file = ASSETS_DIR / f"voiceover_{timestamp}.json"
    voiceover_file.write_text(json.dumps(voiceover_data, indent=2), encoding="utf-8")

    # Save lesson text
    lesson_file = ASSETS_DIR / f"lesson_{timestamp}.txt"
    lesson_file.write_text(current_lesson, encoding="utf-8")

    # --- Step 4: Upload everything to Google Drive ---
    files_to_upload = [video_path, str(code_file), str(voiceover_file), str(lesson_file)]
    if audio_path and Path(audio_path).exists():
        files_to_upload.append(audio_path)

    print(f"[Action 4] Uploading {len(files_to_upload)} file(s) to Google Drive 'JESUS' folder...")
    try:
        results = upload_to_jesus_folder(files_to_upload)
        print(f"[Action 4] ✅ All files uploaded to Google Drive!")
        for r in results:
            print(f"  - {r.get('name')}: https://drive.google.com/file/d/{r.get('id')}/view")
    except Exception as e:
        print(f"[Action 4] ERROR: Google Drive upload failed: {e}")
        print("[Action 4] Files are available locally as artifacts.")
        # Don't exit — still clean up state

    # --- Step 5: Archive lesson & clear state ---
    print("[Action 4] Archiving lesson and clearing state...")
    archive_current_lesson()
    clear_current_unpolished_code()
    clear_current_perfect_code()
    clear_current_voiceover()

    print("[Action 4] ✅ Pipeline complete! State cleared. Ready for next lesson.")
    print("[Action 4] → Run Action 1 to start the next lesson.")


if __name__ == "__main__":
    main()
