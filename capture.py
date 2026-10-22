import logging
from PIL import ImageGrab
from pathlib import Path
import config


def capture_screen(output_path: Path = config.SCREENSHOT_PATH) -> bool:
    """
    Captures the primary monitor and saves it to output_path.
    Returns:
        bool: True if capture was successful, False otherwise.
    """
    try:
        logging.info("Initiating screen capture...")
        # Ensure parent directories exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        import platform
        import subprocess
        
        current_os = platform.system()
        temp_raw_path = output_path.with_suffix(".raw.png")
        
        if current_os == "Darwin":
            # On macOS, use the native /usr/sbin/screencapture utility directly.
            screencapture_bin = "/usr/sbin/screencapture"
            if not Path(screencapture_bin).exists():
                screencapture_bin = "screencapture" # fallback
            
            cmd = [screencapture_bin, "-x", str(temp_raw_path)]
            logging.info(f"Running macOS screencapture command: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            capture_success = (result.returncode == 0 and temp_raw_path.exists())
        else:
            # Fallback to Pillow's ImageGrab logic on Windows
            screenshot = ImageGrab.grab()
            screenshot.save(temp_raw_path, "PNG")
            capture_success = temp_raw_path.exists()

        if capture_success:
            # Load captured image and save it as a compressed JPEG to output_path
            logging.info("Compressing screenshot to JPEG format...")
            from PIL import Image
            with Image.open(temp_raw_path) as img:
                # Convert to RGB (required for JPEGs)
                rgb_img = img.convert("RGB")
                # Save with quality=60 to reduce bandwidth
                rgb_img.save(output_path, "JPEG", quality=60)
            
            # Clean up temporary raw file
            try:
                temp_raw_path.unlink()
            except Exception as clean_err:
                logging.warning(f"Could not delete temp raw file: {clean_err}")
                
            logging.info(f"Screenshot captured and compressed successfully: {output_path} ({output_path.stat().st_size / 1024:.2f} KB)")
            return True
        else:
            logging.error("Native screenshot capture failed.")
            return False
            
    except Exception as e:
        logging.error(f"Error capturing screen: {e}")
        if platform.system() == "Darwin":
            logging.error(
                "Security Tip: If on macOS, make sure your terminal application or python runner "
                "has 'Screen Recording' permissions enabled under System Settings > Privacy & Security."
            )
        return False

# Manual test run
if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_screenshot.png"
        if capture_screen(test_file):
            print("Capture test passed!")
        else:
            print("Capture test failed.")
