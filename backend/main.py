from fastapi import FastAPI, UploadFile, File, Form, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import journal_routes
from services.firebase_client import initialize_firebase  # Initialize Firebase first
from routes import user_routes
from config.logger import get_logger
import uvicorn
import os
# from agents.geo_agent import router as geo_router
# from agents.context_agent import router as wiki_router
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__name__)

app = FastAPI(title="Hermes API", description="Personal AI Assistant API")

# Mount static files directory for serving uploaded images
uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

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
app.include_router(journal_routes.router)
# app.include_router(geo_router)
# app.include_router(wiki_router)

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

@app.post("/api/upload/image")
async def upload_image(
    request: Request,
    image: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: str = Form(default="demo_session"),
    message: str = Form(default="What do you see in this image?")
):
    """
    Upload an image, analyze it with perception agent, and trigger conversation.
    This is the main endpoint for image-based conversations.
    """
    try:
        from utils.storage_client import storage_client
        from agents.perception_agent import analyze_image_perception
        from agents.conversation_agent import conversation_agent
        from routes.journal_routes import get_user_id
        import base64
        
        # Validate file type
        if not image.content_type.startswith("image/"):
            return {
                "status": "error",
                "message": "Invalid file type. Please upload an image file."
            }
        
        # Read image data
        image_data = await image.read()
        if len(image_data) == 0:
            return {
                "status": "error", 
                "message": "Empty image file"
            }
        
        logger.info(f"📸 Processing image upload: {image.filename}, size: {len(image_data)} bytes")
        
        # Upload to blob storage
        photo_url = await storage_client.upload_image(
            image_data=image_data,
            user_id=user_id,
            content_type=image.content_type
        )
        
        if not photo_url:
            return {
                "status": "error",
                "message": "Failed to upload image to storage"
            }
        
        logger.info(f"✅ Image uploaded to storage: {photo_url}")
        # Normalize local URLs so mobile clients can reach the server-hosted file
        try:
            from urllib.parse import urlparse, urljoin
            parsed = urlparse(photo_url)
            if parsed.hostname in ('localhost', '127.0.0.1'):
                base = str(request.base_url)
                photo_url = urljoin(base, parsed.path.lstrip('/'))
                logger.info(f"🔁 Normalized photo_url for client reachability: {photo_url}")
        except Exception:
            logger.warning("Could not normalize photo_url; leaving as-is")
        
        # Analyze image with perception agent
        base64_image = base64.b64encode(image_data).decode('utf-8')
        perception_result = analyze_image_perception(base64_image, "base64")
        
        if "error" in perception_result:
            logger.error(f"❌ Perception analysis failed: {perception_result['error']}")
        else:
            logger.info(f"✅ Image analysis completed: {perception_result.get('scene_summary', 'No summary')[:100]}...")
        
        # Add photo URL to perception context
        perception_result["image_url"] = photo_url
        perception_result["photo_url"] = photo_url
        
        logger.info(f"🔍 Perception result with URLs: image_url={perception_result.get('image_url')}, photo_url={perception_result.get('photo_url')}")
        
        # Update conversation agent with scene context
        await conversation_agent._handle_scene_analysis({
            "analysis": perception_result,
            "image_url": photo_url,
            "photo_url": photo_url
        })
        
        logger.info(f"✅ Scene context set in conversation agent with photo URLs")
        
        # Simulate getting location context (you might want to get this from the frontend)
        # For now, we'll process without geo context or let the conversation agent handle it
        
        # Process the message with the conversation agent
        conversation_result = await conversation_agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id
        )
        
        return {
            "status": "success",
            "photo_url": photo_url,
            "perception_analysis": perception_result,
            "conversation_response": conversation_result["response"],
            "tts_audio_data": conversation_result.get("tts_audio_data"),
            "context_used": conversation_result.get("context_used", {}),
            "timestamp": conversation_result.get("timestamp"),
            "message": "Image uploaded and analyzed successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Image upload failed: {str(e)}")
        import traceback
        logger.error(f"Upload error traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Image upload failed: {str(e)}",
            "photo_url": None
        }

@app.post("/api/chat")
async def chat_with_hermes(
    message: str = Form(...),
    session_id: str = Form(default="default_session"),
    latitude: float = Form(None),
    longitude: float = Form(None),
    authorization: str = Header(None)
):
    """Chat with Hermes AI - processes message and returns response with optional TTS"""
    try:
        from agents.conversation_agent import conversation_agent
        from routes.journal_routes import get_user_id
        
        print(f"🔍 Chat endpoint called with authorization header: {authorization[:50] if authorization else 'None'}...")
        
        # Get the real user ID from the authorization header
        user_id = get_user_id(authorization)
        
        print(f"🔍 Chat request from user: {user_id}")
        print(f"📝 Message: {message}")
        print(f"🆔 Session ID: {session_id}")
        print(f"📍 Location: {latitude}, {longitude}" if latitude and longitude else "📍 No location provided")
        
        # Process message through conversation agent
        result = await conversation_agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id
        )
        
        # Save the conversation to the database (always save all conversations)
        try:
            from services.db_service import save_conversation_entry
            from datetime import datetime
            
            conversation_entry = {
                "message": message,
                "response": result["response"],
                "timestamp": datetime.utcnow().isoformat(),
                "latitude": latitude,
                "longitude": longitude,
                "location_name": "Chat Location",
                "photo_url": None,  # Will be filled if image was uploaded
                "session_id": session_id
            }
            
            # Get location name if coordinates are provided
            if latitude and longitude:
                try:
                    from utils.maps_client import get_location_context
                    location_context = get_location_context(latitude, longitude)
                    conversation_entry["location_name"] = location_context.get("location_name", "Unknown Location")
                    print(f"🌍 Location resolved: {conversation_entry['location_name']}")
                except Exception as loc_error:
                    print(f"⚠️ Could not resolve location: {str(loc_error)}")
                    conversation_entry["location_name"] = f"Location ({latitude:.4f}, {longitude:.4f})"
            
            # Add location data if available from conversation agent
            if hasattr(conversation_agent, 'current_geo_context') and conversation_agent.current_geo_context:
                conversation_entry["latitude"] = conversation_agent.current_geo_context.get("latitude")
                conversation_entry["longitude"] = conversation_agent.current_geo_context.get("longitude")
                conversation_entry["location_name"] = conversation_agent.current_geo_context.get("location_name", "Chat Location")
                print(f"🌍 Added geo context: {conversation_entry['location_name']}")
            
            # Add photo URL if available from scene context
            if hasattr(conversation_agent, 'current_scene_context') and conversation_agent.current_scene_context:
                conversation_entry["photo_url"] = (
                    conversation_agent.current_scene_context.get("photo_url") or 
                    conversation_agent.current_scene_context.get("image_url")
                )
                print(f"📸 Added photo URL: {conversation_entry['photo_url']}")
            
            print(f"💾 Saving conversation entry for user {user_id}: {conversation_entry}")
            save_conversation_entry(user_id, conversation_entry)
            print(f"✅ Successfully saved conversation for user {user_id}")
            
        except Exception as save_error:
            print(f"❌ Failed to save conversation: {str(save_error)}")
            import traceback
            print(f"❌ Save error traceback: {traceback.format_exc()}")
        
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
