import logging
import platform
import subprocess
import shlex


def speak(text: str) -> bool:
    """
    Speaks the provided text aloud.
    Uses 'say' command on macOS, PowerShell SpeechSynthesizer on Windows.
    Returns:
        bool: True if narration started successfully, False otherwise.
    """
    if not text or not text.strip():
        logging.warning("Empty text passed for narration. Skipping.")
        return False
        
    current_os = platform.system()
    logging.info(f"Initiating narration on {current_os}...")
    
    try:
        if current_os == "Darwin":
            # Using list form of subprocess.run without shell=True avoids argument/string escaping bugs.
            # This is resilient to special characters or spaces.
            cmd = ["say", text]
            logging.info("Executing native macOS 'say' command...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                logging.info("Narration finished successfully.")
                return True
            else:
                logging.error(f"macOS 'say' command failed: {result.stderr.decode('utf-8')}")
                return False
                
        elif current_os == "Windows":
            # Encode command as UTF-16LE base64 to safely handle any special characters
            # (apostrophes, quotes, unicode, etc.) in the narration text without escaping issues.
            import base64
            # Build a PowerShell here-string @'...'@ which accepts all characters as-is
            ps_script = (
                "Add-Type -AssemblyName System.Speech; "
                "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(@'\n"
                + text +
                "\n'@)"
            )
            encoded = base64.b64encode(ps_script.encode("utf-16-le")).decode("ascii")
            cmd = ["powershell", "-EncodedCommand", encoded]
            
            logging.info("Executing Windows PowerShell SpeechSynthesizer command...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                logging.info("Narration finished successfully.")
                return True
            else:
                logging.error(f"Windows PowerShell speech command failed: {result.stderr.decode('utf-8')}")
                return False
        else:
            logging.warning(f"TTS is not natively implemented for OS: {current_os}")
            print(f"[OS: {current_os}] TTS Narration: {text}")
            return True
            
    except Exception as e:
        logging.error(f"Exception during narration execution: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    print("Testing speak module...")
    speak("Hello! This is a test narration from the screen reader application.")
