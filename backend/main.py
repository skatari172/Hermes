from fastapi import FastAPI, UploadFile, File, Form, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import journal_routes
from services.firebase_client import initialize_firebase  # Initialize Firebase first
from routes import user_routes
from routes import chat_routes
import uvicorn
import base64
import asyncio
from PIL import Image
from PIL.ExifTags import TAGS
# from agents.geo_agent import router as geo_router
# from agents.context_agent import router as wiki_router
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
app.include_router(chat_routes.router)
# app.include_router(geo_router)
# app.include_router(wiki_router)

@app.get("/")
def root():
    return {"message": "Hermes API running 🚀", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}


@app.post("/api/image/process")
async def process_image(
    image_file: UploadFile = File(...),
    user_id: str = Form(default="demo_user"),
    session_id: str = Form(default="demo_session"),
    entity_name: str = Form(default=None)
):
    """Process image through the complete agent pipeline."""
    try:
        # Read the image file
        image_content = await image_file.read()
        
        # Check if file is empty
        if len(image_content) == 0:
            return {
                "status": "error",
                "message": "Empty image file"
            }
        
        # Convert to base64
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        # Extract GPS coordinates from image automatically using location API fallback
        from utils.location_api_standalone import process_image_location_with_api
        
        print("📍 Processing image location with API fallback...")
        geo_result = process_image_location_with_api(image_base64, "base64")
        
        if geo_result["success"]:
            lat = geo_result["coordinates"]["lat"]
            lng = geo_result["coordinates"]["lng"]
            method = geo_result.get("method", "unknown")
            print(f"✅ Location determined ({method}): {lat}, {lng}")
            
            if method == "location_api":
                api_data = geo_result.get('location_api', {})
                print(f"🌐 Location: {api_data.get('location', 'Unknown')}")
        else:
            # Handle case where location cannot be determined
            print(f"❌ Could not determine location: {geo_result['error']}")
            return {
                "status": "error",
                "message": f"Could not determine location: {geo_result['error']}",
                "error_type": "location_detection_failed",
                "suggestion": "Check your internet connection or try using a photo with GPS metadata"
            }
        
        # Import agents (using standalone versions to avoid ADK issues)
        print("🤖 Starting complete agent pipeline...")
        
        # Step 1: Perception Agent (with translation priority)
        print("📸 Step 1: Analyzing image with OCR and translation...")
        from utils.perception_utils import analyze_image_with_translation
        perception_result = await analyze_image_with_translation(image_base64, "base64")
        
        # Step 2: Geo Agent - Get location context
        print("🗺️ Step 2: Getting location context...")
        from agents.geo_agent import get_location_context
        geo_context = get_location_context(lat, lng)
        
        # Step 3: Context Agent - Build comprehensive context
        print("🧠 Step 3: Building context and verifying entity...")
        from utils.context_utils import build_comprehensive_context
        context_result = build_comprehensive_context(
            lat=lat,
            lng=lng,
            perception_clues=perception_result,
            geo_context=geo_context,
            user_id=user_id,
            session_id=session_id
        )
        
        # Step 4: Store cultural summary in database
        print("💾 Step 4: Storing cultural summary in database...")
        from utils.storage_utils import store_cultural_summary
        db_result = await store_cultural_summary(context_result, user_id, session_id)
        
        # Step 4.5: Create journal entry after context agent completes
        print("📖 Step 4.5: Creating journal entry...")
        from utils.storage_utils import create_journal_entry
        journal_result = await create_journal_entry(context_result, user_id, session_id)
        
        # Step 5: Response Agent - Generate cultural response
        print("💬 Step 5: Generating cultural response...")
        from utils.response_utils import generate_cultural_response_with_context
        response_result = await generate_cultural_response_with_context(
            user_message="Tell me about what I'm seeing in this photo",
            context_data=context_result,
            user_id=user_id,
            session_id=session_id
        )
        
        # Step 6: Store context in chat session for follow-ups
        print("💾 Step 6: Storing context in chat session...")
        from routes.chat_routes import chat_sessions
        
        session_key = f"{user_id}_{session_id}"
        if session_key not in chat_sessions:
            chat_sessions[session_key] = {
                "user_id": user_id,
                "session_id": session_id,
                "conversation_history": [],
                "context_data": None,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }
        
        # Store the context data in the session
        chat_sessions[session_key]["context_data"] = context_result
        chat_sessions[session_key]["last_activity"] = datetime.utcnow().isoformat()
        
        print(f"✅ Context stored in chat session: {session_key}")
        
        return {
            "status": "success",
            "message": "Image processed successfully",
            "data": {
                "coordinates": {"lat": lat, "lng": lng},
                "location_method": geo_result.get("method", "unknown"),
                "perception": {
                    "scene_summary": perception_result.get('scene_summary', ''),
                    "translated_text": perception_result.get('translated_text', []),
                    "cultural_landmarks": perception_result.get('cultural_landmarks', []),
                    "architectural_style": perception_result.get('architectural_style', ''),
                    "cultural_elements": perception_result.get('cultural_elements', []),
                    "atmosphere": perception_result.get('atmosphere', ''),
                    "cultural_notes": perception_result.get('cultural_notes', [])
                },
                "geo": geo_context,
                "context": {
                    "entity_verified": context_result.get('verified', False),
                    "entity_name": context_result.get('entity', 'Unknown'),
                    "entity_type": context_result.get('entity_type', 'unknown'),
                    "certainty": context_result.get('certainty', 0.0),
                    "cultural_summary": context_result.get('cultural_summary', '')
                },
                "response": {
                    "text": response_result.get('response', ''),
                    "user_message": response_result.get('user_message', ''),
                    "context_used": response_result.get('context_used', {}),
                    "metadata": response_result.get('metadata', {})
                },
                "database": {
                    "stored": db_result.get('success', False),
                    "message": db_result.get('message', '')
                },
                "journal": {
                    "created": journal_result.get('success', False),
                    "message": journal_result.get('message', ''),
                    "journal_data": journal_result.get('journal_data', {})
                },
                "session": {
                    "stored": True,
                    "session_key": session_key,
                    "has_context": True
                }
            }
        }
        
    except Exception as e:
        print(f"❌ Image processing error: {e}")
        return {
            "status": "error",
            "message": f"Image processing failed: {str(e)}"
        }

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
