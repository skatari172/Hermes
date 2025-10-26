"""
Voice interaction routes for Hermes AI Cultural Companion.
Handles speech-to-text and text-to-speech endpoints.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from utils.auth_util import verify_firebase_token
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import io
import base64

from utils.elevenlabs_client import elevenlabs_client
from config.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

@router.post("/speak")
async def text_to_speech(
    text: str = Form(...),
    voice_id: Optional[str] = Form(None),
    user_id: str = Depends(verify_firebase_token),
    session_id: str = Form(...),
    speed: Optional[float] = Form(1.0)
):
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        text: Text to convert to speech
        voice_id: Optional voice ID (uses default if not provided)
        user_id: User identifier
        session_id: Session identifier
        speed: Speech speed multiplier (1.0 = normal, >1.0 = faster, <1.0 = slower)
        
    Returns:
        Audio stream in MP3 format
    """
    try:
        logger.info(f"TTS request for user {user_id}: {text[:50]}...")
        
        # Generate audio bytes
        audio_bytes = await elevenlabs_client.text_to_speech(
            text=text,
            voice_id=voice_id,
            speed=speed
        )

        # Return base64-encoded audio in JSON for easier consumption by mobile clients
        try:
            b64 = base64.b64encode(audio_bytes).decode('utf-8')
            return {"status": "success", "audio_data": b64}
        except Exception:
            # Fallback to streaming response if base64 encoding fails
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=hermes_response.mp3",
                    "Cache-Control": "no-cache"
                }
            )
        
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

@router.post("/speak/stream")
async def text_to_speech_stream(
    text: str = Form(...),
    voice_id: Optional[str] = Form(None),
    user_id: str = Depends(verify_firebase_token),
    session_id: str = Form(...),
    speed: Optional[float] = Form(1.0)
):
    """
    Stream text-to-speech conversion for real-time audio.
    
    Args:
        text: Text to convert to speech
        voice_id: Optional voice ID (uses default if not provided)
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Streaming audio response
    """
    try:
        logger.info(f"Streaming TTS request for user {user_id}: {text[:50]}...")
        
        async def generate_audio():
            try:
                async for chunk in elevenlabs_client.stream_text_to_speech(
                    text=text,
                    voice_id=voice_id,
                    speed=speed
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"TTS streaming error: {str(e)}")
                yield b""  # Empty chunk to end stream
        
        return StreamingResponse(
            generate_audio(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=hermes_response.mp3",
                "Cache-Control": "no-cache",
                "Transfer-Encoding": "chunked"
            }
        )
        
    except Exception as e:
        logger.error(f"TTS streaming setup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS streaming failed: {str(e)}")

@router.post("/chat")
async def voice_chat(
    message: str = Form(...),
    user_id: str = Depends(verify_firebase_token),
    session_id: str = Form(...),
    voice_id: Optional[str] = Form(None),
    stream_audio: bool = Form(False)
):
    """
    Process voice/text message and return both text and audio response.
    Placeholder - not yet implemented.
    """
    return {
        "text_response": "Chat endpoint placeholder - coming soon",
        "error": "This endpoint requires conversation agent implementation"
    }

@router.get("/voices")
async def get_available_voices():
    """
    Get list of available voices from ElevenLabs.
    
    Returns:
        List of available voices with metadata
    """
    try:
        voices = await elevenlabs_client.get_available_voices()
        return {
            "voices": voices,
            "default_voice": "adam",
            "default_voice_id": "pNInz6obpgDQGcFmaJgB"
        }
    except Exception as e:
        logger.error(f"Error fetching voices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch voices: {str(e)}")

@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    user_id: str = Depends(verify_firebase_token),
    session_id: str = Form(default="demo_session")
):
    """
    Transcribe audio file to text using ElevenLabs STT API.
    
    Args:
        audio_file: Audio file to transcribe
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Transcribed text
    """
    try:
        logger.info(f"Transcription request from user {user_id}")
        
        # Read audio file
        audio_content = await audio_file.read()
        logger.info(f"Received audio file: {audio_file.filename}, size: {len(audio_content)} bytes")
        logger.info(f"Audio file content type: {audio_file.content_type}")
        logger.info(f"First 20 bytes: {audio_content[:20]}")
        logger.info(f"Last 20 bytes: {audio_content[-20:]}")
        
        # Check if file is empty
        if len(audio_content) == 0:
            logger.error("❌ Audio file is empty!")
            raise HTTPException(status_code=400, detail="Audio file is empty")
        
        # Check if file is too small
        if len(audio_content) < 1000:
            logger.error(f"❌ Audio file too small: {len(audio_content)} bytes")
            raise HTTPException(status_code=400, detail=f"Audio file too small: {len(audio_content)} bytes")
        
        # Check for valid audio headers
        if audio_content[:4] != b'RIFF':
            logger.warning(f"⚠️ File doesn't start with RIFF header. First 4 bytes: {audio_content[:4]}")
            if audio_content[:3] == b'ID3':
                logger.info("🔍 Detected MP3 format")
            elif audio_content[:4] == b'ftyp':
                logger.info("🔍 Detected MP4/M4A format")
            else:
                logger.warning(f"🔍 Unknown format. First 10 bytes: {audio_content[:10]}")
        else:
            logger.info("✅ Valid WAV file detected")
        
        # Use ElevenLabs STT API for real transcription
        try:
            from utils.elevenlabs_client import elevenlabs_client
            
            if elevenlabs_client.client:
                # Use ElevenLabs STT API
                transcription_result = await elevenlabs_client.speech_to_text(audio_content)
                
                transcribed_text = transcription_result["text"]
                confidence = transcription_result["confidence"]
                language = transcription_result["language_code"]
                
                logger.info(f"ElevenLabs STT result: {transcribed_text}")
                
                return {
                    "transcribed_text": transcribed_text,
                    "confidence": confidence,
                    "language": language,
                    "timestamp": "2024-01-01T00:00:00Z",
                    "file_size": len(audio_content),
                    "method": "elevenlabs_stt"
                }
            else:
                raise Exception("ElevenLabs client not available")
                
        except Exception as stt_error:
            logger.warning(f"ElevenLabs STT failed: {stt_error}, falling back to simulation")
            
            # Fallback to simple simulation if STT fails
            if len(audio_content) < 10000:  # Short recording
                transcribed_text = "Hello, this is a short message."
            elif len(audio_content) < 50000:  # Medium recording
                transcribed_text = "This is a medium length voice message that was recorded and transcribed."
            else:  # Long recording
                transcribed_text = "This is a longer voice message that demonstrates the speech-to-text transcription functionality. The system is working correctly and can process audio input."
            
            return {
                "transcribed_text": transcribed_text,
                "confidence": 0.5,
                "language": "en-US",
                "timestamp": "2024-01-01T00:00:00Z",
                "file_size": len(audio_content),
                "method": "simulation_fallback",
                "error": str(stt_error)
            }
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/clear-context")
async def clear_conversation_context(
    user_id: str = Depends(verify_firebase_token),
    session_id: str = Form(...)
):
    """
    Clear conversation context for a session.
    Placeholder - not yet implemented.
    """
    return {
        "message": "Context clear endpoint placeholder - coming soon",
        "user_id": user_id,
        "session_id": session_id
    }
