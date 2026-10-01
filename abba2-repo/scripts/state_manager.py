"""
ABBA 2 — State File Manager
Handles reading/writing of lesson, code, and voiceover state files.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_DIR = REPO_ROOT / "state"

# State file paths
FORMER_LESSONS_FILE = STATE_DIR / "former_lessons.txt"
CURRENT_LESSON_FILE = STATE_DIR / "current_lesson.txt"
CURRENT_UNPOLISHED_CODE_FILE = STATE_DIR / "current_unpolished_code.py"
CURRENT_PERFECT_CODE_FILE = STATE_DIR / "current_perfect_code.py"
CURRENT_VOICEOVER_FILE = STATE_DIR / "current_voiceover.json"


# ── Lesson helpers ──────────────────────────────────────────────────────────

def read_current_lesson() -> str:
    content = CURRENT_LESSON_FILE.read_text(encoding="utf-8").strip()
    return content


def write_current_lesson(lesson_text: str):
    CURRENT_LESSON_FILE.write_text(lesson_text.strip() + "\n", encoding="utf-8")
    print(f"[State] Current lesson written ({len(lesson_text)} chars)")


def clear_current_lesson():
    CURRENT_LESSON_FILE.write_text("", encoding="utf-8")
    print("[State] Current lesson cleared")


def is_current_lesson_empty() -> bool:
    return read_current_lesson() == ""


def archive_current_lesson():
    """Move current lesson to former_lessons.txt then clear current."""
    lesson = read_current_lesson()
    if not lesson:
        print("[State] No current lesson to archive.")
        return
    former = FORMER_LESSONS_FILE.read_text(encoding="utf-8")
    separator = "\n\n" + "=" * 60 + "\n\n"
    FORMER_LESSONS_FILE.write_text(former.rstrip() + separator + lesson + "\n", encoding="utf-8")
    clear_current_lesson()
    print("[State] Lesson archived to former_lessons.txt")


def extract_lesson_from_response(response_text: str) -> str:
    """Extract lesson content from AI response using delimiters."""
    match = re.search(
        r"====LESSON START====\s*(.*?)\s*====LESSON END====",
        response_text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not find ====LESSON START==== ... ====LESSON END==== in response")
    return f"====LESSON START====\n{match.group(1).strip()}\n====LESSON END===="


# ── Code helpers ─────────────────────────────────────────────────────────────

def read_current_unpolished_code() -> str:
    return CURRENT_UNPOLISHED_CODE_FILE.read_text(encoding="utf-8").strip()


def write_current_unpolished_code(code: str):
    CURRENT_UNPOLISHED_CODE_FILE.write_text(code.strip() + "\n", encoding="utf-8")
    print(f"[State] Unpolished code written ({len(code)} chars)")


def clear_current_unpolished_code():
    CURRENT_UNPOLISHED_CODE_FILE.write_text(
        "# ABBA 2 — Current Unpolished Code\n# Empty — no code in progress.\n",
        encoding="utf-8",
    )
    print("[State] Unpolished code cleared")


def is_unpolished_code_empty() -> bool:
    content = read_current_unpolished_code()
    # Consider it empty if it's just the header comment
    return content == "" or content.startswith("# ABBA 2") and "Empty" in content


def extract_code_from_response(response_text: str) -> str:
    """Extract Python code from AI response."""
    match = re.search(
        r"====CODE START====\s*(.*?)\s*====CODE END====",
        response_text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not find ====CODE START==== ... ====CODE END==== in response")
    return match.group(1).strip()


def read_current_perfect_code() -> str:
    return CURRENT_PERFECT_CODE_FILE.read_text(encoding="utf-8").strip()


def write_current_perfect_code(code: str):
    CURRENT_PERFECT_CODE_FILE.write_text(code.strip() + "\n", encoding="utf-8")
    print(f"[State] Perfect code written ({len(code)} chars)")


def clear_current_perfect_code():
    CURRENT_PERFECT_CODE_FILE.write_text(
        "# ABBA 2 — Current Perfect Code\n# Empty — no polished code ready.\n",
        encoding="utf-8",
    )
    print("[State] Perfect code cleared")


def is_perfect_code_empty() -> bool:
    content = read_current_perfect_code()
    return content == "" or (content.startswith("# ABBA 2") and "Empty" in content)


def extract_perfect_code_from_response(response_text: str) -> str:
    match = re.search(
        r"====PERFECT CODE START====\s*(.*?)\s*====PERFECT CODE END====",
        response_text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not find ====PERFECT CODE START==== ... ====PERFECT CODE END==== in response")
    return match.group(1).strip()


# ── Voiceover helpers ────────────────────────────────────────────────────────

def read_current_voiceover() -> list:
    content = CURRENT_VOICEOVER_FILE.read_text(encoding="utf-8").strip()
    if not content or content == "[]":
        return []
    return json.loads(content)


def write_current_voiceover(voiceover_data: list):
    CURRENT_VOICEOVER_FILE.write_text(json.dumps(voiceover_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[State] Voiceover JSON written ({len(voiceover_data)} entries)")


def clear_current_voiceover():
    CURRENT_VOICEOVER_FILE.write_text("[]\n", encoding="utf-8")
    print("[State] Voiceover cleared")


def extract_voiceover_from_response(response_text: str) -> list:
    match = re.search(
        r"====VOICEOVER JSON START====\s*(.*?)\s*====VOICEOVER JSON END====",
        response_text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not find ====VOICEOVER JSON START==== ... ====VOICEOVER JSON END==== in response")
    raw = match.group(1).strip()
    return json.loads(raw)


# ── Former lessons ────────────────────────────────────────────────────────────

def read_former_lessons() -> str:
    return FORMER_LESSONS_FILE.read_text(encoding="utf-8")
