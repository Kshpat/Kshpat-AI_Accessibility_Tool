# Implementation Plan - Image-to-Speech MVP

We will develop a lightweight Python-based tool in `/Users/harsh/Desktop/MDM` that implements the screen-to-speech loop.

## Proposed Architecture

1. **Hotkey / Trigger**: We will implement a dual approach, working on both Windows and macOS:
   - **Command Line interface (CLI)**: A simple command that runs one cycle immediately. This is robust, requires no system-level permissions, and is perfect for testing.
   - **Hotkey daemon**: A background script using `pynput` that listens for the key combo (e.g., `Cmd + Option + S` on Mac, or `Ctrl + Alt + S` on Windows).
2. **Screen Capture**: A module using `Pillow` (PIL) `ImageGrab`. It works natively out-of-the-box on both Windows and macOS.
3. **AI Description**: A module using the Gemini API. We will use the standard HTTP API via `requests` to send the image to `gemini-2.5-flash`.
4. **Text to Speech**:
   - On **macOS**: Invoke the native `say` command via `subprocess`.
   - On **Windows**: Invoke a PowerShell command (`SpeechSynthesizer`) via `subprocess`, or use `pyttsx3`. To keep things dependency-free and lightweight, we can run PowerShell speech engine via python `subprocess`, ensuring it works out-of-the-box on Windows without extra installs.


---

## Proposed Changes

### [MVP Codebase]

We will create a structured python package in `/Users/harsh/Desktop/MDM/` with:

#### [NEW] [requirements.txt](file:///Users/harsh/Desktop/MDM/requirements.txt)
Holds dependencies: `pillow`, `requests`, `python-dotenv`, `pynput`.

#### [NEW] [config.py](file:///Users/harsh/Desktop/MDM/config.py)
Configuration wrapper loaded from `.env` (Gemini API Key, prompt templates, temporary file paths).

#### [NEW] [.env.example](file:///Users/harsh/Desktop/MDM/.env.example)
Example environment template with space for `GEMINI_API_KEY`.

#### [NEW] [capture.py](file:///Users/harsh/Desktop/MDM/capture.py)
Logic to capture the screen and save to a temporary file.

#### [NEW] [analyzer.py](file:///Users/harsh/Desktop/MDM/analyzer.py)
Logic to encode the captured image as base64 and send it to the Gemini API (`gemini-2.5-flash`) for description.

#### [NEW] [narrator.py](file:///Users/harsh/Desktop/MDM/narrator.py)
Logic using the macOS `say` subprocess to read texts.

#### [NEW] [main.py](file:///Users/harsh/Desktop/MDM/main.py)
Direct execution CLI and background hotkey listener logic.

#### [NEW] [setup.sh](file:///Users/harsh/Desktop/MDM/setup.sh)
Script to automate python environment creation, package installation, and configuration setup.

---

## Verification Plan

### Automated/Manual verification
1. Run `python3 main.py --once` to capture the screen, call the API, and read the description aloud immediately.
   - Verify that python outputs the description to stdout.
   - Verify that audio is heard.
2. Run `python3 main.py --listen` (hotkey listener).
   - Press the configured hotkey.
   - Verify it triggers screen capture, API call, and read aloud.
   - *Note*: macOS security prompts for screen capture and accessibility may pop up; we will include instructions on resolving these.
