"""
Voice interaction routes for Hermes AI Cultural Companion.
Handles speech-to-text, conversation, and text-to-speech endpoints.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import io
import base64

from agents.conversation_agent import conversation_agent
from utils.elevenlabs_client import elevenlabs_client
from config.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

@router.post("/speak")
async def text_to_speech(
    text: str = Form(...),
    voice_id: Optional[str] = Form(None),
    user_id: str = Form(...),
    session_id: str = Form(...)
):
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        text: Text to convert to speech
        voice_id: Optional voice ID (uses default if not provided)
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Audio stream in MP3 format
    """
    try:
        logger.info(f"TTS request for user {user_id}: {text[:50]}...")
        
        # Generate audio
        audio_bytes = await elevenlabs_client.text_to_speech(
            text=text,
            voice_id=voice_id
        )
        
        # Return audio as streaming response
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
    user_id: str = Form(...),
    session_id: str = Form(...)
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
                    voice_id=voice_id
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
    user_id: str = Form(...),
    session_id: str = Form(...),
    voice_id: Optional[str] = Form(None),
    stream_audio: bool = Form(False)
):
    """
    Process voice/text message and return both text and audio response.
    
    Args:
        message: User's message (text or transcribed speech)
        user_id: User identifier
        session_id: Session identifier
        voice_id: Optional voice ID for TTS
        stream_audio: Whether to stream audio response
        
    Returns:
        JSON with text response and audio data/URL
    """
    try:
        logger.info(f"Voice chat request from user {user_id}: {message[:50]}...")
        
        # Process message through conversation agent
        response_data = await conversation_agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id
        )
        
        response_text = response_data["response"]
        
        # Generate audio response
        if stream_audio:
            # For streaming, return text immediately and provide audio endpoint
            return {
                "text_response": response_text,
                "audio_url": f"/api/voice/speak/stream?text={response_text}&voice_id={voice_id}&user_id={user_id}&session_id={session_id}",
                "context_used": response_data.get("context_used", {}),
                "timestamp": response_data.get("timestamp")
            }
        else:
            # Generate audio synchronously
            audio_bytes = await elevenlabs_client.text_to_speech(
                text=response_text,
                voice_id=voice_id
            )
            
            # Encode audio as base64 for JSON response
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return {
                "text_response": response_text,
                "audio_data": audio_base64,
                "audio_format": "mp3",
                "context_used": response_data.get("context_used", {}),
                "timestamp": response_data.get("timestamp")
            }
        
    except Exception as e:
        logger.error(f"Voice chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Voice chat failed: {str(e)}")

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
    user_id: str = Form(...),
    session_id: str = Form(...)
):
    """
    Transcribe audio file to text (placeholder for future implementation).
    
    Args:
        audio_file: Audio file to transcribe
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Transcribed text
    """
    try:
        # TODO: Implement actual speech-to-text transcription
        # For now, return a placeholder response
        logger.info(f"Transcription request from user {user_id}")
        
        # Read audio file
        audio_content = await audio_file.read()
        
        # Placeholder: In a real implementation, you would:
        # 1. Use Google Speech-to-Text API or similar
        # 2. Process the audio content
        # 3. Return the transcribed text
        
        return {
            "transcribed_text": "This is a placeholder transcription. Please implement actual STT service.",
            "confidence": 0.0,
            "language": "en-US",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/clear-context")
async def clear_conversation_context(
    user_id: str = Form(...),
    session_id: str = Form(...)
):
    """
    Clear conversation context for a session.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Success confirmation
    """
    try:
        await conversation_agent.clear_context()
        logger.info(f"Context cleared for user {user_id}, session {session_id}")
        
        return {
            "message": "Context cleared successfully",
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Context clear error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear context: {str(e)}")
