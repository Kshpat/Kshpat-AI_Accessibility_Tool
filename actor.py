import logging
import asyncio
import time
import requests
import pyautogui
import base64
import sys

from winrt.windows.media.ocr import OcrEngine
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.storage import StorageFile

import config
import narrator

logger = logging.getLogger(__name__)

def get_target_text(command: str, image_path) -> str:
    """Uses the configured AI model to find the exact on-screen text matching the user's intent."""
    is_ok, err_msg = config.validate_config()
    if not is_ok:
        logger.error(err_msg)
        return ""

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    prompt = (
        f"The user gave the voice command: '{command}'.\n"
        f"Look at the screen. What is the EXACT TEXT of the label, button, or input field they want to interact with?\n"
        f"Reply ONLY with the exact text string as it appears on the screen, nothing else. "
        f"For example, if they want to click login, reply 'Login'. If they want the username field, reply 'Username'."
    )

    try:
        if config.AI_PROVIDER == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": config.OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        ],
                    }
                ],
                "max_tokens": 20
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")
            
        elif config.AI_PROVIDER == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            groq_models = list(dict.fromkeys([config.GROQ_MODEL, "qwen/qwen3.8-27b"]))
            for model_name in groq_models:
                payload = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                            ],
                        }
                    ],
                    "max_tokens": 20
                }
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")
                    else:
                        logger.warning(f"Groq target extraction error {resp.status_code} on {model_name}")
                except Exception as e:
                    logger.warning(f"Groq exception on {model_name}: {e}")
            # All Groq models failed — fall back to Gemini for target extraction
            logger.warning("All Groq models failed for target extraction. Falling back to Gemini...")
            gemini_models = list(dict.fromkeys([config.GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.6-flash"]))
            gemini_headers = {"Content-Type": "application/json"}
            gemini_payload = {"contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}]}]}
            for gm in gemini_models:
                try:
                    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{gm}:generateContent?key={config.GEMINI_API_KEY}", headers=gemini_headers, json=gemini_payload, timeout=30)
                    if r.status_code == 200:
                        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"').strip("'")
                except Exception:
                    pass
            
        elif config.AI_PROVIDER == "gemini":
            models_to_try = [config.GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
            models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
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
            for model_name in models_to_try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_name}:generateContent?key={config.GEMINI_API_KEY}"
                )
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        res_data = resp.json()
                        target = res_data["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"').strip("'")
                        logger.info(f"Gemini target text extraction succeeded using {model_name}: '{target}'")
                        return target
                    else:
                        logger.warning(f"Gemini target extraction error {resp.status_code} on {model_name}")
                except Exception as e:
                    logger.warning(f"Exception extracting target text via {model_name}: {e}")

        return ""
    except Exception as e:
        logger.error(f"Failed to parse target text: {e}")
        return ""

async def find_text_coordinates(image_path, target_text: str):
    """Uses Windows Native OCR to find the bounding box of the target text."""
    target_text = target_text.lower()
    
    file = await StorageFile.get_file_from_path_async(str(image_path.resolve()))
    stream = await file.open_read_async()
    decoder = await BitmapDecoder.create_async(stream)
    software_bitmap = await decoder.get_software_bitmap_async()
    
    engine = OcrEngine.try_create_from_user_profile_languages()
    if not engine:
        logger.error('OCR Engine not available.')
        return None
        
    result = await engine.recognize_async(software_bitmap)
    
    # Try exact match first
    for line in result.lines:
        if line.text.lower().strip() == target_text:
            return _get_center(line)
            
    # Try partial match (word by word)
    for line in result.lines:
        if target_text in line.text.lower():
            for word in line.words:
                if word.text.lower() in target_text or target_text in word.text.lower():
                    return _get_center_word(word)
    return None

def _get_center(line):
    # Rough center based on first and last word in the line
    words_count = line.words.size if hasattr(line.words, 'size') else len(line.words)
    if words_count == 0:
        return (0, 0)
    first_word = line.words[0].bounding_rect
    last_word = line.words[words_count - 1].bounding_rect
    x = first_word.x + (last_word.x + last_word.width - first_word.x) / 2
    y = first_word.y + first_word.height / 2
    return (x, y)

def _get_center_word(word):
    rect = word.bounding_rect
    return (rect.x + rect.width / 2, rect.y + rect.height / 2)

def perform_action(command: str):
    """Parses intent, finds UI element via OCR, and clicks it."""
    logger.info(f"Processing command: '{command}'")
    
    # Step 1: Ask AI what text to look for
    target_text = get_target_text(command, config.SCREENSHOT_PATH)
    if not target_text:
        narrator.speak("I'm sorry, I couldn't figure out what element to click.")
        return
        
    logger.info(f"Target text identified as: '{target_text}'")
    
    # Step 2: Use OCR to find coords
    try:
        coords = asyncio.run(find_text_coordinates(config.SCREENSHOT_PATH, target_text))
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        coords = None
        
    if coords:
        x, y = coords
        # Adjust y slightly down to click the actual input field if it's a label
        # (Heuristic: If it's a field label, the input box is often below or to the right)
        # We'll just click directly on the text for now.
        
        logger.info(f"Moving mouse and clicking at {x}, {y}")
        narrator.speak(f"Clicking on {target_text}")
        
        # Move smoothly and click
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        narrator.speak("Done")
    else:
        logger.error(f"Could not find '{target_text}' on screen.")
        narrator.speak(f"I couldn't find {target_text} on the screen.")
