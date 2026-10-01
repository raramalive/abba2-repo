"""
ABBA 2 — Action 3: Render Low-Quality Video & Polish Code
1. Renders the unpolished Manim code at low quality (-ql)
2. Sends video + code to Kie.ai Gemini Flash 3.8 for polishing
3. Saves perfect code to state/current_perfect_code.py
4. Saves voiceover JSON to state/current_voiceover.json
Only runs if current_unpolished_code.py is NOT empty AND current_perfect_code.py IS empty.
"""

import sys
import os
import subprocess
import shutil
import glob
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from state_manager import (
    is_unpolished_code_empty,
    is_perfect_code_empty,
    read_current_unpolished_code,
    extract_perfect_code_from_response,
    extract_voiceover_from_response,
    write_current_perfect_code,
    write_current_voiceover,
)
from kie_client import polish_code_with_video

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
RENDER_DIR = Path("/tmp/manim_render")
SCENE_FILE = RENDER_DIR / "scene.py"


def render_low_quality(python_code: str) -> str:
    """Render Manim scene at low quality and return path to output video."""
    RENDER_DIR.mkdir(parents=True, exist_ok=True)

    # Write scene file
    SCENE_FILE.write_text(python_code, encoding="utf-8")
    print(f"[Action 3] Scene file written to {SCENE_FILE}")

    # Detect scene class name (look for 'class ... (Scene)')
    import re
    match = re.search(r"class\s+(\w+)\s*\(.*Scene.*\)", python_code)
    if match:
        scene_class = match.group(1)
    else:
        scene_class = "MainScene"
    print(f"[Action 3] Detected scene class: {scene_class}")

    # Run Manim at low quality
    cmd = [
        "manim",
        "-ql",              # low quality
        "--media_dir", str(RENDER_DIR / "media"),
        str(SCENE_FILE),
        scene_class,
    ]
    print(f"[Action 3] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)

    print("[Action 3] STDOUT:", result.stdout[-3000:] if result.stdout else "(none)")
    print("[Action 3] STDERR:", result.stderr[-2000:] if result.stderr else "(none)")

    if result.returncode != 0:
        raise RuntimeError(
            f"Manim rendering failed (exit {result.returncode}).\n"
            f"STDERR: {result.stderr[-1000:]}"
        )

    # Find output video
    media_dir = RENDER_DIR / "media"
    video_files = list(media_dir.rglob("*.mp4"))
    if not video_files:
        # Also check for .mov
        video_files = list(media_dir.rglob("*.mov"))

    if not video_files:
        raise RuntimeError(f"No video output found in {media_dir}")

    # Take the most recently modified video
    video_path = max(video_files, key=lambda p: p.stat().st_mtime)
    print(f"[Action 3] Rendered video: {video_path}")

    # Copy to accessible location
    output_video = RENDER_DIR / "output_low_quality.mp4"
    shutil.copy(video_path, output_video)
    return str(output_video)


def main():
    print("=" * 60)
    print("ABBA 2 — Action 3: Render Low-Quality & Polish")
    print("=" * 60)

    if is_unpolished_code_empty():
        print("[Action 3] current_unpolished_code.py is EMPTY. Nothing to render.")
        print("[Action 3] Run Action 2 first to generate code.")
        sys.exit(0)

    if not is_perfect_code_empty():
        print("[Action 3] current_perfect_code.py already has content. Skipping.")
        print("[Action 3] Proceed to Action 4 (High Quality Render & Upload).")
        sys.exit(0)

    # Load unpolished code
    unpolished_code = read_current_unpolished_code()
    print(f"[Action 3] Unpolished code loaded ({len(unpolished_code)} chars)")

    # Render low-quality video
    print("[Action 3] Rendering low-quality video...")
    try:
        video_path = render_low_quality(unpolished_code)
    except Exception as e:
        print(f"[Action 3] Render failed: {e}")
        print("[Action 3] Attempting to continue with Kie.ai using code only (no video)...")
        video_path = None

    # Load polish prompt
    polish_prompt_file = PROMPTS_DIR / "Code Polisher Prompt.txt"
    if not polish_prompt_file.exists():
        print(f"[Action 3] ERROR: Polish prompt not found at {polish_prompt_file}")
        sys.exit(1)
    polish_prompt = polish_prompt_file.read_text(encoding="utf-8")

    # If we have a video, send it; otherwise send just the code
    if video_path and Path(video_path).exists():
        print("[Action 3] Sending video + code to Kie.ai Gemini Flash 3.8...")
        response = polish_code_with_video(polish_prompt, video_path, unpolished_code)
    else:
        print("[Action 3] No video available — sending text-only polish request to Kie.ai...")
        from kie_client import _rotator, _gemini_request
        final_prompt = polish_prompt.replace("{{code_here}}", unpolished_code)
        final_prompt += "\n\n(NOTE: No video was available for this run. Please fix the code based on code review alone.)"

        contents = [{"role": "user", "parts": [{"text": final_prompt}]}]

        def _attempt(api_key):
            return _gemini_request(api_key, contents)

        response = _rotator.call_with_rotation(_attempt)

    print(f"[Action 3] Kie.ai response received ({len(response)} chars)")

    # Extract perfect code
    print("[Action 3] Extracting perfect code...")
    perfect_code = extract_perfect_code_from_response(response)
    write_current_perfect_code(perfect_code)
    print("[Action 3] ✅ Perfect code saved to state/current_perfect_code.py")

    # Extract voiceover JSON
    print("[Action 3] Extracting voiceover JSON...")
    try:
        voiceover_data = extract_voiceover_from_response(response)
        write_current_voiceover(voiceover_data)
        print(f"[Action 3] ✅ Voiceover JSON saved ({len(voiceover_data)} sections)")
    except Exception as e:
        print(f"[Action 3] WARNING: Could not extract voiceover JSON: {e}")
        print("[Action 3] Voiceover will be empty — continuing.")

    print("[Action 3] → Action 4 (High Quality Render & Upload) should now run.")


if __name__ == "__main__":
    main()
