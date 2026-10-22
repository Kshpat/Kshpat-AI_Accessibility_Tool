import logging
import threading
import sounddevice as sd
import speech_recognition as sr
import time
import narrator

logger = logging.getLogger(__name__)

is_listening = False
stop_listening_flag = False
_stop_func = None

class SoundDeviceMic(sr.AudioSource):
    """A Microphone class for speech_recognition that uses sounddevice to avoid PyAudio."""
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024):
        self.device_index = device_index
        self.format = sr.AudioData
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2 # 16-bit
        self._sd_stream = None
        self.stream = None
        
    def __enter__(self):
        self._sd_stream = sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.CHUNK,
            device=self.device_index,
            channels=1,
            dtype='int16'
        )
        self._sd_stream.start()
        
        class StreamProxy:
            def __init__(self, sd_stream):
                self.sd_stream = sd_stream
            def read(self, size):
                data, overflow = self.sd_stream.read(size)
                return bytes(data)
                
        self.stream = StreamProxy(self._sd_stream)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._sd_stream is not None:
            self._sd_stream.stop()
            self._sd_stream.close()
            self._sd_stream = None
            self.stream = None

def listen_loop(callback):
    """
    Listens for a single sentence immediately, says 'Okay', and executes the task.
    """
    global is_listening
    if is_listening:
        return
        
    is_listening = True
    logger.info("Initializing voice listener... Listening for a single command now.")
    threading.Thread(target=_listen_once, args=(callback,), daemon=True).start()

def _listen_once(callback):
    global is_listening
    
    r = sr.Recognizer()
    mic = SoundDeviceMic()
    
    try:
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("[Mic] Ready. Listening for command...")
            # Wait up to 15 seconds for someone to start speaking, 
            # and limit the phrase to 15 seconds.
            audio = r.listen(source, timeout=15, phrase_time_limit=15)
            
        logger.info("[Mic] Processing speech...")
        text = r.recognize_google(audio).lower().strip()
        logger.info(f"[Mic] Heard command: '{text}'")
        
        if text:
            narrator.speak("Okay")
            try:
                callback(text)
            except Exception as e:
                logger.error(f"Action Error: {e}")
                
    except sr.WaitTimeoutError:
        logger.info("[Mic] Timed out waiting for speech.")
    except sr.UnknownValueError:
        logger.info("[Mic] Could not understand audio.")
    except Exception as e:
        logger.error(f"Listener error: {e}")
    finally:
        is_listening = False
        logger.info("Voice listener shut down.")

def stop_listening():
    # No longer needed for one-shot listening, but kept for compatibility
    pass
