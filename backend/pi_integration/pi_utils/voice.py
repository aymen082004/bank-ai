import os
import json
import numpy as np

# Make pywhispercpp optional
try:
    import librosa
    from pywhispercpp.model import Model
    PYWHISPER_AVAILABLE = True
except ImportError:
    PYWHISPER_AVAILABLE = False
    librosa = None
    Model = None

from .llm import call_llm

MODEL_PATH = r"C:\Users\Abbas\.lmstudio\models\vonjack\whisper-large-v3-gguf\whisper-large-v3-q8_0.gguf"

# Lazy loading - don't load at import time to avoid memory issues
whisper_model = None
_model_loading_attempted = False

def _load_whisper_model():
    """Lazy load the Whisper model when first needed."""
    global whisper_model, _model_loading_attempted
    
    if _model_loading_attempted:
        return whisper_model
    
    _model_loading_attempted = True
    
    if not PYWHISPER_AVAILABLE:
        print("Voice: pywhispercpp not available")
        return None
    
    if not os.path.exists(MODEL_PATH):
        print(f"Voice: Model not found at {MODEL_PATH}")
        return None
    
    try:
        print("Voice: Loading Whisper model (this may take a moment)...")
        whisper_model = Model(MODEL_PATH)
        print("Voice: Whisper model loaded successfully")
        return whisper_model
    except Exception as e:
        print(f"Voice: Error loading Whisper model: {e}")
        print("Voice: Voice transcription will be unavailable")
        whisper_model = None
        return None

def transcribe_tunisian(audio_path):
    """
    Transcribes audio to Tunisian text using a local GGUF model.
    Bypasses FFmpeg by using librosa to decode audio to a 16kHz numpy array.
    """
    # Lazy load the model
    model = _load_whisper_model()
    if not model:
        return "Error: Voice transcription unavailable. The Whisper model could not be loaded due to memory constraints."

    try:
        # Check if file exists
        if not os.path.exists(audio_path):
            return f"Error: Audio file not found at {audio_path}"

        # Use librosa to decode the audio file to a 16kHz numpy array
        # librosa (via soundfile/audioread) can handle many formats.
        # We use sr=16000 as required by Whisper.
        try:
            audio_array, _ = librosa.load(audio_path, sr=16000)
        except Exception as e:
            # If librosa fails, it's likely due to missing ffmpeg/decoders for webm.
            # In this case, we try to see if it's a wav file or use a simpler decoder.
            return f"Audio Decoding Error: {str(e)}. Please ensure the audio format is supported or FFmpeg is available."
        
        if len(audio_array) == 0:
            return "Error: Audio file is empty or could not be decoded."

        # Transcribe the numpy array
        # We can specify the language to improve accuracy
        segments = model.transcribe(audio_array, language="ar")
        
        # Combine segments
        transcription = "".join([s.text for s in segments])
        
        # Strip potential whitespace
        transcription = transcription.strip()
        
        return transcription
    except Exception as e:
        return f"Error transcribing with GGUF: {str(e)}"

def normalize_intent(tunisian_text):
    """
    Uses LLM to normalize Tunisian dialect to structured intent.
    """
    prompt = f"""
    Translate and normalize this Tunisian dialect sentence into structured JSON.
    Tunisian: "{tunisian_text}"
    
    Return ONLY JSON with "goal" and "budget".
    Example: {{"goal": "car", "budget": 30000}}
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages)
    
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        return json.loads(response[start:end])
    except:
        return {"goal": None, "budget": None}
