import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve project path and load .env file
project_root = Path(__file__).resolve().parent
load_dotenv(project_root / ".env")

# ── AI Provider Selection ──────────────────────────────────────────────────────
# Set AI_PROVIDER to one of: "openrouter", "groq", "gemini"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter").strip().lower()

# ── OpenRouter Settings (default - free, no credit card) ──────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
# Free vision model on OpenRouter (200 req/day free, no card needed)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free").strip()

# ── Groq Settings (free, fast, no credit card) ────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct").strip()

# ── Gemini Settings (fallback) ────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()

# ── Shared Settings ───────────────────────────────────────────────────────────
NARRATION_PROMPT = os.getenv(
    "NARRATION_PROMPT",
    "You are looking at a computer screen. Provide a clear, natural-language description "
    "of the screen's content for a visually impaired person. Focus on crucial UI elements, "
    "readable text (OCR), layout, icons, open apps, and the current active task. Be concise but descriptive."
).strip()

# Setup paths
TEMP_DIR = project_root / "temp"
TEMP_DIR.mkdir(exist_ok=True)
SCREENSHOT_PATH = TEMP_DIR / "screenshot.jpg"


def validate_config() -> tuple[bool, str]:
    """Checks if the active provider's API key is set. Returns (is_ok, error_message)."""
    if AI_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            return False, (
                "OPENROUTER_API_KEY is not set.\n"
                "  >> Get a FREE key at: https://openrouter.ai/keys\n"
                "  >> Then add it to your .env file."
            )
    elif AI_PROVIDER == "groq":
        if not GROQ_API_KEY:
            return False, (
                "GROQ_API_KEY is not set.\n"
                "  >> Get a FREE key at: https://console.groq.com/keys\n"
                "  >> Then add it to your .env file."
            )
    elif AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            return False, (
                "GEMINI_API_KEY is not set.\n"
                "  >> Get a key at: https://aistudio.google.com/app/apikey\n"
                "  >> Then add it to your .env file."
            )
    else:
        return False, f"Unknown AI_PROVIDER: '{AI_PROVIDER}'. Choose from: openrouter, groq, gemini"
    return True, ""
