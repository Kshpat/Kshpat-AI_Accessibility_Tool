# Project Plan: Image-to-Speech Screen Reader MVP (Cross-Platform)

This document provides a complete, step-by-step implementation plan for an MVP that allows visually impaired users to capture their screen via a hotkey, scan it with Gemini Vision (`gemini-2.5-flash`), and read the description aloud using native system Text-to-Speech (TTS).

---

## 1. System Requirements & Platform Integration

- **OS Support**: macOS (using native `say` command) and Windows (using PowerShell `SpeechSynthesizer` or `pyttsx3`).
- **Python Version**: Python 3.9+ (matches standard macOS version 3.9.6).
- **Core Dependencies**:
  - `Pillow` (for cross-platform screen capture)
  - `requests` (for lightweight Gemini API HTTP requests without version-specific SDK issues)
  - `python-dotenv` (for API key management)
  - `pynput` (for global hotkey listening)

---

## 2. File Structure

We will create the following files in the project root `/Users/harsh/Desktop/MDM`:

```text
MDM/
├── .env.example        # Environment variables template
├── .env                # Local configuration (Git ignored)
├── requirements.txt    # Project dependencies
├── config.py           # Configuration loader
├── capture.py          # Screen capturing interface
├── analyzer.py         # Gemini API vision analyzer
├── narrator.py         # Cross-platform TTS engine
├── main.py             # CLI runner and Hotkey daemon
└── setup.sh            # One-click environment bootstrap tool
```

---

## 3. Detailed Component Plan & Code Structures

### A. Dependencies (`requirements.txt`)
Contains standard python packages:
```text
pillow>=9.0.0
requests>=2.28.0
python-dotenv>=1.0.0
pynput>=1.7.6
```

### B. Configuration Loader (`config.py`)
Loads settings from `.env`. Must support custom prompts for visual impairment audio descriptions:
- **Default Prompt**: *"You are looking at a computer screen. Provide a clear, natural-language description of the screen's content for a visually impaired person. Focus on crucial UI elements, readable text (OCR), layout, icons, open apps, and the current active task. Be concise but descriptive."*

### C. Screen Capture (`capture.py`)
Uses Pillow's `ImageGrab.grab()` to take a screenshot and returns the file path of the saved PNG/JPG image in a temp folder.

### D. Gemini Vision Analyzer (`analyzer.py`)
Sends the screenshot to Gemini API using a standard POST request:
- Convert image to Base64.
- Model: `gemini-2.5-flash` via API endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}`.
- Send the prompt and the base64 media chunk.
- Yields the generated description text.

### E. TTS Engine (`narrator.py`)
Detects the OS using `platform.system()` and runs TTS offline:
- **macOS**: `subprocess.run(["say", text])`
- **Windows**: `subprocess.run(["powershell", "-Command", f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')"]` (escaping quotes safely).

### F. Application Core (`main.py`)
Integrates the modules and supports two CLI flags:
1. `--once`: Take a screenshot, analyze it, speak, and exit immediately. (Safe for testing).
2. `--listen`: Runs a loop with `pynput` listener waiting for a global hotkey (e.g. `Ctrl + Alt + S` / `Cmd + Option + S`). When triggered, it spawns a background thread to process screen-to-speech to prevent UI/input blocking.

### G. Setup Boostrap (`setup.sh`/`setup.bat`)
A shell script to create Python `venv`, activate it, install dependencies, and create the `.env` skeleton.

---

## 4. Run & Test Instructions

### Step 1: Setup
Run the bootstrap setup in the terminal:
```bash
chmod +x setup.sh && ./setup.sh
```

### Step 2: API Configuration
Edit the generated `.env` file to add your API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### Step 3: Run Single Test
Test the capturing and reading flow immediately:
```bash
source venv/bin/activate
python3 main.py --once
```

### Step 4: Run Background Listener
Run the hotkey listener daemon:
```bash
python3 main.py --listen
```
Press **Cmd + Option + S** (on macOS) or **Ctrl + Alt + S** (on Windows) to trigger reading of whatever screen you are on.

---

## 5. Security & Permissions Checklist for Next Developer
- **Screen Recording Permission**: On macOS, Python (or the terminal running it) will prompt for "Screen Recording" permission upon first capture. The user must enable this under *System Settings > Privacy & Security > Screen Recording*.
- **Accessibility Permission**: Global hotkey monitoring via `pynput` requires "Accessibility" permissions on macOS under *System Settings > Privacy & Security > Accessibility*.
