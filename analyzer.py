import base64
import logging
import requests
from pathlib import Path
import config


def encode_image(image_path: Path) -> str:
    """Encodes an image file to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# ── Provider-specific analyzers ───────────────────────────────────────────────

def _analyze_via_openrouter(base64_image: str) -> str:
    """Sends image to OpenRouter API (OpenAI-compatible format)."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MDM-ScreenReader",
        "X-Title": "MDM Screen Reader",
    }
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": config.NARRATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
    }
    logging.info(f"Sending request to OpenRouter ({config.OPENROUTER_MODEL})...")
    response = requests.post(url, headers=headers, json=payload, timeout=45)

    if response.status_code == 200:
        res_data = response.json()
        try:
            description = res_data["choices"][0]["message"]["content"]
            logging.info("OpenRouter analysis completed successfully.")
            return description.strip()
        except (KeyError, IndexError) as e:
            logging.error(f"Failed to parse OpenRouter response: {res_data}. Error: {e}")
            return "Error: Could not parse response from OpenRouter API."
    else:
        logging.error(f"OpenRouter API error {response.status_code}: {response.text[:300]}")
        return f"Error: OpenRouter API request failed with status {response.status_code}."


def _analyze_via_groq(base64_image: str) -> str:
    """Sends image to Groq API with model fallback, then falls back to Gemini if all Groq models fail."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # Try primary Groq model first, then fallback Groq models
    groq_models = list(dict.fromkeys([config.GROQ_MODEL, "qwen/qwen3.8-27b"]))

    for model_name in groq_models:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": config.NARRATION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 512,
        }
        logging.info(f"Sending request to Groq ({model_name})...")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                description = response.json()["choices"][0]["message"]["content"]
                logging.info(f"Groq analysis completed successfully using {model_name}.")
                return description.strip()
            else:
                logging.warning(f"Groq error {response.status_code} on {model_name}: {response.text[:150]}")
        except Exception as e:
            logging.warning(f"Groq exception on {model_name}: {e}")

    # All Groq models failed — fall back to Gemini
    logging.warning("All Groq models failed. Falling back to Gemini API...")
    return _analyze_via_gemini(base64_image)


def _analyze_via_gemini(base64_image: str) -> str:
    """Sends image to Gemini API with automatic model fallback on temporary 503 errors."""
    models_to_try = [config.GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
    # Deduplicate preserving order
    models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": config.NARRATION_PROMPT},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_image,
                        }
                    },
                ]
            }
        ]
    }

    last_error = ""
    for model_name in models_to_try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={config.GEMINI_API_KEY}"
        )
        logging.info(f"Sending request to Gemini API ({model_name})...")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                description = res_data["candidates"][0]["content"]["parts"][0]["text"]
                logging.info(f"Gemini analysis completed successfully using {model_name}.")
                return description.strip()
            else:
                last_error = f"Gemini API error {response.status_code} on model {model_name}: {response.text[:200]}"
                logging.warning(last_error)
        except Exception as e:
            last_error = f"Exception requesting {model_name}: {e}"
            logging.warning(last_error)

    return f"Error: Gemini API request failed. {last_error}"


# ── Main entry point ──────────────────────────────────────────────────────────

def analyze_screenshot(image_path: Path = config.SCREENSHOT_PATH) -> str:
    """
    Sends the screenshot to the configured AI provider and returns a text description.
    Provider is selected via AI_PROVIDER in config / .env.
    Returns:
        str: Description of the screenshot, or an error message if it fails.
    """
    is_ok, err_msg = config.validate_config()
    if not is_ok:
        logging.error(err_msg)
        return f"Configuration Error: {err_msg}"

    if not image_path.exists():
        msg = f"Screenshot file not found at {image_path}."
        logging.error(msg)
        return msg

    try:
        logging.info(f"Encoding screenshot (provider: {config.AI_PROVIDER})...")
        base64_image = encode_image(image_path)

        if config.AI_PROVIDER == "openrouter":
            return _analyze_via_openrouter(base64_image)
        elif config.AI_PROVIDER == "groq":
            return _analyze_via_groq(base64_image)
        elif config.AI_PROVIDER == "gemini":
            return _analyze_via_gemini(base64_image)
        else:
            return f"Error: Unknown provider '{config.AI_PROVIDER}'"

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error: {e}")
        return f"Network Error: {e}"
    except Exception as e:
        logging.error(f"Unexpected error during analysis: {e}")
        return f"Unexpected Error: {e}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    print(f"Testing analyze_screenshot (provider: {config.AI_PROVIDER})...")
    if config.SCREENSHOT_PATH.exists():
        desc = analyze_screenshot(config.SCREENSHOT_PATH)
        print("--- Description Output ---")
        print(desc)
    else:
        print(f"Skipping test run (no screenshot found at {config.SCREENSHOT_PATH}).")
