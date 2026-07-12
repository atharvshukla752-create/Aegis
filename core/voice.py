import threading
import os
import tempfile
import pyttsx3
from gtts import gTTS
from playsound import playsound

# English TTS engine (offline, instant)
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 175)
tts_engine.setProperty('volume', 1.0)

# Pre-generated Hindi audio path
_hindi_audio_ready = threading.Event()
_hindi_audio_path = None


def speak_english(text):
    """Speak text in English using offline TTS — instant"""
    def _run():
        tts_engine.say(text)
        tts_engine.runAndWait()
    threading.Thread(target=_run, daemon=True).start()


def prepare_hindi_audio(text):
    """
    Pre-generate Hindi audio in background WHILE Aegis is still typing reply.
    Call this as soon as you have the text — don't wait.
    """
    global _hindi_audio_path
    _hindi_audio_ready.clear()

    def _run():
        global _hindi_audio_path
        try:
            tts = gTTS(text=text, lang='hi')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                temp_path = f.name
            tts.save(temp_path)
            _hindi_audio_path = temp_path
        except Exception as e:
            print(f"Hindi prep error: {e}")
            _hindi_audio_path = None
        finally:
            _hindi_audio_ready.set()

    threading.Thread(target=_run, daemon=True).start()


def speak_hindi_prepared():
    """Play the pre-generated Hindi audio — near instant since it's already ready"""
    def _run():
        _hindi_audio_ready.wait(timeout=10)  # wait max 10 seconds
        if _hindi_audio_path and os.path.exists(_hindi_audio_path):
            try:
                playsound(_hindi_audio_path)
                os.remove(_hindi_audio_path)
            except Exception as e:
                print(f"Hindi play error: {e}")
    threading.Thread(target=_run, daemon=True).start()


def speak_hindi(text):
    """Fallback — generate and play Hindi audio (has delay)"""
    def _run():
        try:
            tts = gTTS(text=text, lang='hi')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                temp_path = f.name
            tts.save(temp_path)
            playsound(temp_path)
            os.remove(temp_path)
        except Exception as e:
            print(f"Hindi voice error: {e}")
    threading.Thread(target=_run, daemon=True).start()


def speak(text, hindi=False):
    """Main speak function — auto picks language"""
    if hindi:
        speak_hindi(text)
    else:
        speak_english(text)