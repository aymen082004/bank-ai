"""
Voice transcription using local Whisper model
"""
import os
import tempfile
import jwt
from rest_framework.decorators import api_view
from rest_framework.response import Response
import subprocess
import logging

logger = logging.getLogger(__name__)

# Get JWT secret from environment (same as other endpoints)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")

# Path to the local Whisper model
WHISPER_MODEL_PATH = r"C:\Users\Abbas\.lmstudio\models\vonjack\whisper-large-v3-gguf\whisper-large-v3-q8_0.gguf"


@api_view(['POST'])
def transcribe_audio(request):
    # Manual JWT authentication (same as other endpoints)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response({'error': 'Authentication required'}, status=401)
    
    token = auth_header.split(" ")[1]
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return Response({'error': 'Invalid or expired token'}, status=401)
    """
    Transcribe audio file using local Whisper model via pywhispercpp
    """
    try:
        if 'audio' not in request.FILES:
            return Response({'error': 'No audio file provided'}, status=400)
        
        audio_file = request.FILES['audio']
        
        # Save uploaded file temporarily
        temp_path = os.path.join(tempfile.gettempdir(), audio_file.name)
        with open(temp_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
        
        # Convert audio to WAV format (Whisper requires 16kHz mono WAV)
        wav_path = temp_path.replace('.webm', '.wav')
        
        try:
            # Convert webm to wav using ffmpeg
            result = subprocess.run([
                'ffmpeg', '-y', '-i', temp_path, 
                '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', 
                wav_path
            ], check=True, capture_output=True, text=True, timeout=30)
            logger.info(f"FFmpeg conversion successful: {wav_path}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"FFmpeg conversion failed: {e}")
            # If ffmpeg fails, try using the original file
            wav_path = temp_path
        
        # Try using pywhispercpp (already in requirements)
        try:
            from pywhispercpp.model import Model
            
            # Check if model file exists
            if os.path.exists(WHISPER_MODEL_PATH):
                logger.info(f"Loading Whisper model from: {WHISPER_MODEL_PATH}")
                model = Model(str(WHISPER_MODEL_PATH))
                
                # Transcribe
                segments = model.transcribe(str(wav_path), language="fr")
                transcribed_text = " ".join([segment.text for segment in segments])
                logger.info(f"Transcription successful: {transcribed_text[:50]}...")
            else:
                logger.error(f"Model file not found: {WHISPER_MODEL_PATH}")
                transcribed_text = ""
                
        except ImportError as e:
            logger.warning(f"pywhispercpp not available: {e}")
            # Fallback: use speech_recognition library with Google API
            try:
                import speech_recognition as sr
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                    transcribed_text = recognizer.recognize_google(audio_data, language="fr-FR")
                    logger.info("Speech recognition successful using Google API")
            except ImportError:
                logger.error("speech_recognition library not installed")
                transcribed_text = ""
            except Exception as e:
                logger.error(f"Speech recognition error: {e}")
                transcribed_text = ""
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            transcribed_text = ""
        
        # Cleanup temporary files
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(wav_path) and wav_path != temp_path:
                os.remove(wav_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
        
        if transcribed_text:
            return Response({
                'text': transcribed_text.strip(),
                'success': True
            })
        else:
            return Response({
                'text': '',
                'success': False,
                'message': 'Transcription failed. Please try again.'
            })
        
    except Exception as e:
        logger.error(f"Transcription endpoint error: {e}")
        return Response({'error': str(e)}, status=500)
