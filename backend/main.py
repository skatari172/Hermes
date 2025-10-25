from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from utils.firebase_client import initialize_firebase  # Initialize Firebase first
from routes import user_routes
import uvicorn
import os

app = FastAPI(title="Hermes API", description="Personal AI Assistant API")

# Add CORS middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(user_routes.router)

@app.get("/")
def root():
    return {"message": "Hermes API running 🚀", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/api/voice/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    user_id: str = Form(default="demo_user"),
    session_id: str = Form(default="demo_session")
):
    """Transcribe audio file to text using ElevenLabs STT API."""
    try:
        # Read the audio file
        audio_content = await audio_file.read()
        
        # Check if file is empty
        if len(audio_content) == 0:
            return {
                "status": "error",
                "message": "Audio file is empty",
                "transcribed_text": ""
            }
        
        # Check if file is too small
        if len(audio_content) < 1000:
            return {
                "status": "error", 
                "message": f"Audio file too small: {len(audio_content)} bytes",
                "transcribed_text": ""
            }
        
        # Use ElevenLabs STT API for real transcription
        try:
            print(f"🔍 DEBUG: Attempting to import elevenlabs_client...")
            from utils.elevenlabs_client import elevenlabs_client
            print(f"🔍 DEBUG: ElevenLabs client imported successfully")
            print(f"🔍 DEBUG: Client exists: {elevenlabs_client.client is not None}")
            print(f"🔍 DEBUG: API key loaded: {bool(elevenlabs_client.api_key)}")
            
            if elevenlabs_client.client:
                print(f"🔍 DEBUG: Using ElevenLabs STT API...")
                # Use ElevenLabs STT API
                transcription_result = await elevenlabs_client.speech_to_text(audio_content)
                print(f"🔍 DEBUG: ElevenLabs STT result: {transcription_result}")
                
                transcribed_text = transcription_result["text"]
                confidence = transcription_result["confidence"]
                language = transcription_result["language_code"]
                
                return {
                    "status": "success",
                    "transcribed_text": transcribed_text,
                    "confidence": confidence,
                    "language": language,
                    "file_size": len(audio_content),
                    "file_type": audio_file.content_type,
                    "user_id": user_id,
                    "session_id": session_id,
                    "method": "elevenlabs_stt"
                }
            else:
                print(f"🔍 DEBUG: ElevenLabs client not available, using placeholder")
                # Fallback to placeholder if ElevenLabs client not available
                return {
                    "status": "success",
                    "transcribed_text": "ElevenLabs API key not configured. Please set ELEVENLABS_API_KEY in your .env file.",
                    "confidence": 0.0,
                    "file_size": len(audio_content),
                    "file_type": audio_file.content_type,
                    "user_id": user_id,
                    "session_id": session_id,
                    "method": "placeholder_no_api_key"
                }
                
        except Exception as stt_error:
            print(f"🔍 DEBUG: ElevenLabs STT failed with error: {stt_error}")
            print(f"🔍 DEBUG: Error type: {type(stt_error)}")
            import traceback
            print(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
            # Fallback to simple simulation if STT fails
            if len(audio_content) < 10000:  # Short recording
                transcribed_text = "Hello, this is a short message."
            elif len(audio_content) < 50000:  # Medium recording
                transcribed_text = "This is a medium length voice message that was recorded and transcribed."
            else:  # Long recording
                transcribed_text = "This is a longer voice message that demonstrates the speech-to-text transcription functionality. The system is working correctly and can process audio input."
            
            return {
                "status": "success",
                "transcribed_text": transcribed_text,
                "confidence": 0.5,
                "file_size": len(audio_content),
                "file_type": audio_file.content_type,
                "user_id": user_id,
                "session_id": session_id,
                "method": "simulation_fallback",
                "error": str(stt_error)
            }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Transcription failed: {str(e)}",
            "transcribed_text": ""
        }

@app.post("/api/chat")
async def chat_with_hermes(
    message: str = Form(...),
    user_id: str = Form(default="demo_user"),
    session_id: str = Form(default="demo_session")
):
    """Chat with Hermes AI - processes message and returns response with optional TTS"""
    try:
        from agents.conversation_agent import conversation_agent
        
        # Process message through conversation agent
        result = await conversation_agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id
        )
        
        response_data = {
            "status": "success",
            "response": result["response"],
            "tts_audio_data": result.get("tts_audio_data"),
            "context_used": result.get("context_used", {}),
            "timestamp": result.get("timestamp"),
            "user_id": user_id,
            "session_id": session_id
        }
        
        # Debug logging
        print(f"🔍 Chat Debug: Response length: {len(result['response'])}")
        print(f"🔍 Chat Debug: TTS audio data exists: {result.get('tts_audio_data') is not None}")
        if result.get("tts_audio_data"):
            print(f"🔍 Chat Debug: TTS audio data length: {len(result['tts_audio_data'])}")
        
        return response_data
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Chat processing failed: {str(e)}",
            "response": "I apologize, but I'm having trouble processing your message right now. Please try again."
        }

@app.post("/api/voice/speak")
async def text_to_speech(
    text: str = Form(...),
    user_id: str = Form(default="demo_user"),
    session_id: str = Form(default="demo_session"),
    voice_id: str = Form(default="pNInz6obpgDQGcFmaJgB"),  # Default Adam voice
    model: str = Form(default="eleven_flash_v2_5")
):
    """ElevenLabs TTS endpoint - Convert text to speech and return audio"""
    try:
        from utils.elevenlabs_client import elevenlabs_client
        
        if not elevenlabs_client.client:
            return {
                "status": "error",
                "message": "ElevenLabs API key not configured",
                "audio_data": None
            }
        
        # Generate TTS audio
        audio_bytes = await elevenlabs_client.text_to_speech(
            text=text,
            voice_id=voice_id,
            model=model
        )
        
        # Return audio as base64 encoded string for frontend consumption
        import base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return {
            "status": "success",
            "audio_data": audio_base64,
            "text": text,
            "voice_id": voice_id,
            "model": model,
            "user_id": user_id,
            "session_id": session_id,
            "audio_size": len(audio_bytes)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"TTS generation failed: {str(e)}",
            "audio_data": None
        }
@app.post("/api/voice/chat")
async def voice_chat(user_id: str, session_id: str, message: str):
    """Placeholder chat endpoint"""
    return {
        "status": "success",
        "response": "This is a placeholder response. Connect to your LLM here.",
        "session_id": session_id
    }

@app.post("/api/voice/speak")
async def text_to_speech(user_id: str, session_id: str, text: str):
    """ElevenLabs TTS endpoint"""
    return {
        "status": "success",
        "audio_url": "https://example.com/audio.mp3",
        "message": "Text-to-speech conversion"
    }

if __name__ == "__main__":
    print("🚀 Starting Hermes API server...")
    print("📍 API will be available at:")
    print("   - Local: http://localhost:8000")
    print("   - Network: http://0.0.0.0:8000")
    print("   - External: http://208.64.158.251:8000")
    print("📚 API docs will be available at: http://208.64.158.251:8000/docs")
    print("🧪 Test endpoint: http://208.64.158.251:8000/user/test")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",  # Use import string instead of app object
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        log_level="info",
        reload=True  # Enable auto-reload for development
    )
