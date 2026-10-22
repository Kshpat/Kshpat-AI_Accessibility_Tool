import argparse
import logging
import sys
import threading
import time
import platform
from pynput import keyboard

import config
import capture
import analyzer
import narrator
import listener
import actor

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Thread lock/state to prevent multiple concurrent runs from spamming the hotkey
processing_lock = threading.Lock()
is_processing = False

def run_conversion_flow():
    """Runs a single iteration of capture -> analyze -> narrate."""
    global is_processing
    
    # Try to acquire the execution lock
    with processing_lock:
        if is_processing:
            logging.info("Already processing. Trigger skipped.")
            return
        is_processing = True

    try:
        logging.info("Starting Image-to-Speech conversion flow...")
        
        # 1. Capture screen
        success = capture.capture_screen(config.SCREENSHOT_PATH)
        if not success:
            error_msg = "Screen capture failed. Please check your OS screen recording permissions."
            logging.error(error_msg)
            narrator.speak(error_msg)
            return

        # 2. Analyze screen image
        description = analyzer.analyze_screenshot(config.SCREENSHOT_PATH)
        logging.info(f"Gemini Description: {description}")
        
        # 3. Speak description aloud
        narrator.speak(description)
        
    except Exception as e:
        logging.error(f"Error in execution flow: {e}")
        narrator.speak(f"An unexpected error occurred: {e}")
    finally:
        with processing_lock:
            is_processing = False
        logging.info("Flow processing completed.")
        
        # Start voice command listener after narration
        listener.listen_loop(actor.perform_action)

def trigger_background_flow():
    """Spawns the conversion flow in a background thread to keep hotkey listener responsive."""
    thread = threading.Thread(target=run_conversion_flow, daemon=True)
    thread.start()

def main():
    parser = argparse.ArgumentParser(description="Image-to-Speech Screen Reader MVP (Cross-Platform)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--once",
        action="store_true",
        help="Run the screen-to-speech conversion flow exactly once and exit."
    )
    group.add_argument(
        "--listen",
        action="store_true",
        help="Run as a background hotkey listener daemon."
    )
    args = parser.parse_args()

    # Validate configuration (checks GEMINI_API_KEY)
    is_ok, err_msg = config.validate_config()
    if not is_ok:
        logging.error(err_msg)
        print(f"\n[CONFIG ERROR] {err_msg}\n")
        sys.exit(1)

    if args.once:
        logging.info("Running MVP in single-run mode (--once)...")
        run_conversion_flow()
        # Keep process alive briefly to let narrate command start/finish
        time.sleep(1)
        logging.info("Exiting single-run mode.")
        
    elif args.listen:
        # Determine appropriate hotkey combo by OS
        current_os = platform.system()
        if current_os == "Darwin":
            hotkey_str = "<cmd>+<alt>+s"
        else:
            hotkey_str = "<ctrl>+<alt>+s"

        logging.info(f"Running hotkey listener daemon. Press {hotkey_str} to hear your screen...")
        
        # Setup pynput listener
        # Key modifiers are defined inside angle brackets: e.g. <cmd>, <alt>, <ctrl>
        hotkeys = {
            hotkey_str: trigger_background_flow
        }
        
        try:
            with keyboard.GlobalHotKeys(hotkeys) as listener:
                listener.join()
        except KeyboardInterrupt:
            logging.info("Stopping daemon due to KeyboardInterrupt.")
        except Exception as e:
            logging.error(f"Hotkey listener failed: {e}")
            if current_os == "Darwin":
                logging.error(
                    "Security Tip: Global hotkeys require 'Accessibility' permission on macOS. "
                    "Make sure your terminal application or python runner has accessibility enabled "
                    "under System Settings > Privacy & Security > Accessibility."
                )
            sys.exit(1)

if __name__ == "__main__":
    main()
