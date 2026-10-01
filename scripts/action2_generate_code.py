"""
ABBA 2 — Action 2: Generate Manim Code
Uses v0.app (GPT-5.6-Luna) + Code Gen Prompt + Current Lesson to produce Manim Python code.
Saves code to state/current_unpolished_code.py.
Only runs if current_lesson.txt is NOT empty AND current_unpolished_code.py IS empty.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from state_manager import (
    is_current_lesson_empty,
    is_unpolished_code_empty,
    read_current_lesson,
    extract_code_from_response,
    write_current_unpolished_code,
)
from v0_client import generate_code
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def main():
    print("=" * 60)
    print("ABBA 2 — Action 2: Manim Code Generation")
    print("=" * 60)

    # Check: only proceed if lesson exists but code doesn't yet
    if is_current_lesson_empty():
        print("[Action 2] current_lesson.txt is EMPTY. Nothing to code yet.")
        print("[Action 2] Run Action 1 first to generate a lesson.")
        sys.exit(0)

    if not is_unpolished_code_empty():
        print("[Action 2] current_unpolished_code.py already has content. Skipping.")
        print("[Action 2] Proceed to Action 3 (Render & Polish).")
        sys.exit(0)

    # Load code gen prompt
    code_gen_prompt_file = PROMPTS_DIR / "Initial Code Gen Prompt.txt"
    if not code_gen_prompt_file.exists():
        print(f"[Action 2] ERROR: Code gen prompt not found at {code_gen_prompt_file}")
        sys.exit(1)
    code_gen_prompt = code_gen_prompt_file.read_text(encoding="utf-8")

    # Load current lesson
    current_lesson = read_current_lesson()
    print(f"[Action 2] Current lesson loaded ({len(current_lesson)} chars)")

    # Replace placeholder
    final_prompt = code_gen_prompt.replace("{{lesson_here}}", current_lesson)
    print(f"[Action 2] Prompt prepared ({len(final_prompt)} chars)")

    # Call v0.app
    print("[Action 2] Calling v0.app (GPT-5.6-Luna) for Manim code generation...")
    response = generate_code(final_prompt)

    # Extract code from response
    print("[Action 2] Extracting Python code from response...")
    python_code = extract_code_from_response(response)
    print(f"[Action 2] Code extracted ({len(python_code)} chars)")

    # Save to unpolished code file
    write_current_unpolished_code(python_code)
    print("[Action 2] ✅ Code saved to state/current_unpolished_code.py")
    print("[Action 2] → Action 3 (Render & Polish) should now run.")


if __name__ == "__main__":
    main()
