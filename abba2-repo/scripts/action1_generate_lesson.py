"""
ABBA 2 — Action 1: Generate Lesson
Uses v0.app (GPT-5.6-Luna) + Master Prompt + Former Lessons to produce a new lesson.
Saves lesson to state/current_lesson.txt.
Only runs if current_lesson.txt is EMPTY.
"""

import sys
import os

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(__file__))

from state_manager import (
    is_current_lesson_empty,
    read_former_lessons,
    extract_lesson_from_response,
    write_current_lesson,
)
from v0_client import generate_lesson
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def main():
    print("=" * 60)
    print("ABBA 2 — Action 1: Lesson Generation")
    print("=" * 60)

    # Check: only proceed if no lesson is in progress
    if not is_current_lesson_empty():
        print("[Action 1] current_lesson.txt is NOT empty. Skipping — a lesson is already in progress.")
        print("[Action 1] Proceed to Action 2 (Code Generation).")
        sys.exit(0)

    # Load master prompt
    master_prompt_file = PROMPTS_DIR / "Our Master Prompt.txt"
    if not master_prompt_file.exists():
        print(f"[Action 1] ERROR: Master prompt not found at {master_prompt_file}")
        sys.exit(1)
    master_prompt = master_prompt_file.read_text(encoding="utf-8")
    print(f"[Action 1] Master prompt loaded ({len(master_prompt)} chars)")

    # Load former lessons
    former_lessons = read_former_lessons()
    print(f"[Action 1] Former lessons loaded ({len(former_lessons)} chars)")

    # Call v0.app
    print("[Action 1] Calling v0.app (GPT-5.6-Luna) for lesson generation...")
    response = generate_lesson(master_prompt, former_lessons)

    # Extract lesson from response
    print("[Action 1] Extracting lesson from response...")
    lesson_text = extract_lesson_from_response(response)
    print(f"[Action 1] Lesson extracted ({len(lesson_text)} chars)")

    # Save to current lesson file
    write_current_lesson(lesson_text)
    print("[Action 1] ✅ Lesson saved to state/current_lesson.txt")
    print("[Action 1] → Action 2 (Code Generation) should now run.")


if __name__ == "__main__":
    main()
