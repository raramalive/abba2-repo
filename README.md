# ABBA 2 — AI-Powered Math & Science Video Pipeline

Fully automated pipeline that generates educational Manim animation videos using:
- **v0.app** (GPT-5.6-Luna) for lesson and code generation
- **Kie.ai** (Gemini Flash 3.8) for video analysis and code polishing
- **ElevenLabs** (Alice voice) for voiceover generation
- **Google Drive** for final video storage in the "JESUS" folder

---

## 🔄 Pipeline Overview

The pipeline is split into 4 separate GitHub Actions workflows. **You run each one manually** after the previous completes.

```
Action 1 → Action 2 → Action 3 → Action 4
Lesson     Code       Render LQ   Render HQ
Generation Generation + Polish    + Upload
```

### Action 1: Generate Lesson
- Reads `prompts/Our Master Prompt.txt`
- Attaches `state/former_lessons.txt` (prevents topic repetition)
- Calls v0.app GPT-5.6-Luna to generate a complete lesson
- Saves result to `state/current_lesson.txt`

### Action 2: Generate Manim Code
- Reads `prompts/Initial Code Gen Prompt.txt`
- Injects current lesson into `{{lesson_here}}` placeholder
- Calls v0.app GPT-5.6-Luna to generate Python Manim code
- Saves result to `state/current_unpolished_code.py`

### Action 3: Render Low-Quality & Polish
- Installs Manim + LaTeX + ffmpeg on the runner
- Renders the unpolished code at **low quality** (`manim -ql`)
- Reads `prompts/Code Polisher Prompt.txt` (injects code into `{{code_here}}`)
- Sends video + prompt to **Kie.ai Gemini Flash 3.8**
- Extracts polished Python code → `state/current_perfect_code.py`
- Extracts voiceover JSON → `state/current_voiceover.json`
- Uploads low-quality video as GitHub Actions artifact (for inspection)

### Action 4: High-Quality Render & Upload
- Renders polished code at **high quality** (`manim -qh`)
- Generates voiceover audio via **ElevenLabs** (Alice voice)
- Uploads video + audio + code + lesson to **Google Drive "JESUS" folder**
- Archives lesson to `state/former_lessons.txt`
- Clears all state files for next lesson

---

## 📁 Repository Structure

```
abba2/
├── .github/
│   └── workflows/
│       ├── action1_lesson_generation.yml
│       ├── action2_code_generation.yml
│       ├── action3_render_and_polish.yml
│       └── action4_render_hq_and_upload.yml
├── prompts/
│   ├── Our Master Prompt.txt       ← Master lesson generation prompt
│   ├── Initial Code Gen Prompt.txt ← Manim code generation prompt
│   └── Code Polisher Prompt.txt    ← Code polishing + voiceover prompt
├── scripts/
│   ├── action1_generate_lesson.py
│   ├── action2_generate_code.py
│   ├── action3_render_and_polish.py
│   ├── action4_render_hq_and_upload.py
│   ├── key_manager.py          ← API key rotation
│   ├── state_manager.py        ← State file read/write
│   ├── v0_client.py            ← v0.app API client
│   ├── kie_client.py           ← Kie.ai Gemini client
│   ├── elevenlabs_client.py    ← ElevenLabs TTS client
│   └── gdrive_uploader.py      ← Google Drive uploader
├── secrets/
│   ├── v0_api_keys.json            ← v0.app API keys (rotated)
│   ├── kie_api_keys.json           ← Kie.ai API keys (rotated)
│   ├── elevenlabs_api_keys.json    ← ElevenLabs API keys (rotated)
│   ├── github_token.txt            ← GitHub PAT
│   └── google_service_account.json ← Google service account credentials
└── state/
    ├── former_lessons.txt          ← Archive of all completed lessons
    ├── current_lesson.txt          ← Lesson being worked on (cleared after Action 4)
    ├── current_unpolished_code.py  ← Raw Manim code (cleared after Action 4)
    ├── current_perfect_code.py     ← Polished Manim code (cleared after Action 4)
    └── current_voiceover.json      ← Voiceover JSON (cleared after Action 4)
```

---

## 🚀 How to Run

### Prerequisites
1. Push this repo to GitHub (public repo for unlimited Actions minutes)
2. The `secrets/` directory contains all credentials (already populated)
3. Ensure the Google Service Account has Drive API enabled and access to create files

### Running the Pipeline

Go to **Actions** tab in your GitHub repository:

1. Click **"ABBA2 — Action 1: Generate Lesson"** → **Run workflow**
2. Wait for it to complete (~5-10 min)
3. Click **"ABBA2 — Action 2: Generate Manim Code"** → **Run workflow**
4. Wait for it to complete (~5-10 min)
5. Click **"ABBA2 — Action 3: Render Low-Quality & Polish"** → **Run workflow**
   - ⚠️ This installs LaTeX + Manim which takes ~20-30 min
   - Check the "Artifacts" section for the low-quality preview video
6. Click **"ABBA2 — Action 4: High Quality Render & Upload"** → **Run workflow**
   - ⚠️ High quality render takes ~30-40 min
   - Check your Google Drive "JESUS" folder for the final video

---

## 🔑 API Key Rotation

All API keys are stored in `secrets/` as JSON arrays. The `key_manager.py` script:
- Randomly picks a key for each request
- Rotates to the next key on 401/429 errors
- Retries with exponential backoff

To add more keys, edit the corresponding JSON file and add to the `"keys"` array.

---

## 📝 Lesson State Machine

```
[Empty state]
      ↓ Action 1
current_lesson.txt filled
      ↓ Action 2
current_unpolished_code.py filled
      ↓ Action 3
current_perfect_code.py filled
current_voiceover.json filled
      ↓ Action 4
All state cleared
Lesson added to former_lessons.txt
[Ready for next lesson]
```

Each action is **idempotent** — running it again when already in the right state will skip gracefully.

---

## 🔧 Troubleshooting

**Action 3 fails with Manim error:**
- Check the low-quality render artifact for the error
- The error is usually in the generated Python code (bad LaTeX, wrong API calls)
- Manually edit `state/current_unpolished_code.py` to fix, then re-run Action 3

**Kie.ai returns no delimiters:**
- The response is saved in GitHub Actions logs
- Copy the code manually from logs into `state/current_perfect_code.py`

**Google Drive upload fails:**
- Check the service account has "Drive API" enabled in Google Cloud Console
- Verify the service account email has been shared access to Drive or has organization-wide access

---

## 🎙️ Voiceover Voice

**Alice** — Clear, Engaging Educator  
Voice ID: `Xb7hH8MSUJpSbSDYk0k2`  
Model: `eleven_multilingual_v2` (free tier compatible)

---

## 📺 Output

Each completed lesson produces:
- `ABBA2_lesson_YYYYMMDD_HHMMSS.mp4` — High quality video
- `voiceover_YYYYMMDD_HHMMSS.mp3` — Combined voiceover audio
- `scene_perfect_YYYYMMDD_HHMMSS.py` — Final Manim Python code
- `lesson_YYYYMMDD_HHMMSS.txt` — The lesson text

All uploaded to Google Drive → **JESUS** folder.
