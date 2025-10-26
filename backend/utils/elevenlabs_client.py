"""
ElevenLabs TTS API client for voice synthesis.
Handles text-to-speech conversion using ElevenLabs API.
"""

import os
import io
import asyncio
from typing import Optional, AsyncGenerator
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs
import httpx
from config.settings import get_settings

settings = get_settings()

class ElevenLabsClient:
    """Client for ElevenLabs Text-to-Speech API."""
    
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.default_voice_id = settings.elevenlabs_voice_id
        if not self.api_key:
            # Don't raise error, just log warning
            print("⚠️ ELEVENLABS_API_KEY not found - TTS will not work")
            self.client = None
        else:
            self.client = ElevenLabs(api_key=self.api_key)
    
    async def text_to_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model: str = "eleven_flash_v2_5"  # Updated to use Flash v2.5 for low latency
    ) -> bytes:
        """
        Convert text to speech and return audio bytes.
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID (uses default if not provided)
            model: TTS model to use
            
        Returns:
            Audio bytes in MP3 format
        """
        try:
            if not self.client:
                raise Exception("ElevenLabs client not initialized - check API key")
            
            # Use the client's text_to_speech.convert method (correct API)
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id or self.default_voice_id,
                text=text,
                model_id=model,
                output_format="mp3_44100_128"  # Standard MP3 format
            )
            
            # Collect all audio chunks into bytes
            audio_bytes = b""
            for chunk in audio_generator:
                audio_bytes += chunk
            
            return audio_bytes
            
        except Exception as e:
            raise Exception(f"TTS generation failed: {str(e)}")
    
    async def stream_text_to_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model: str = "eleven_flash_v2_5"  # Updated to use Flash v2.5 for low latency
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream text-to-speech conversion for real-time audio.
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID (uses default if not provided)
            model: TTS model to use
            
        Yields:
            Audio chunks as bytes
        """
        try:
            if not self.client:
                raise Exception("ElevenLabs client not initialized - check API key")
            
            # Use the client's text_to_speech.convert method with streaming
            audio_stream = self.client.text_to_speech.convert(
                voice_id=voice_id or self.default_voice_id,
                text=text,
                model_id=model,
                output_format="mp3_44100_128",  # Standard MP3 format
                stream=True
            )
            
            for chunk in audio_stream:
                yield chunk
                
        except Exception as e:
            raise Exception(f"TTS streaming failed: {str(e)}")
    
    async def get_available_voices(self) -> list:
        """Get list of available voices from ElevenLabs."""
        try:
            if not self.client:
                return []
            
            voices = self.client.voices.get_all()
            return [
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": voice.category,
                    "description": voice.description
                }
                for voice in voices.voices
            ]
        except Exception as e:
            raise Exception(f"Failed to fetch voices: {str(e)}")
    
    def get_voice_by_name(self, name: str) -> Optional[str]:
        """Get voice ID by name."""
        # Common voice mappings for Hermes
        voice_mapping = {
            "adam": "pNInz6obpgDQGcFmaJgB",
            "antoni": "ErXwobaYiN019PkySvjV",
            "arnold": "VR6AewLTigWG4xSOukaG",
            "bella": "EXAVITQu4vr4xnSDxMaL",
            "domi": "AZnzlk1XvdvUeBnXmlld",
            "elli": "MF3mGyEYCl7XYWbV9V6O",
            "josh": "TxGEqnHWrfWFTfGW9XjX",
            "rachel": "21m00Tcm4TlvDq8ikWAM",
            "sam": "yoZ06aMxZJJ28mfd3POQ"
        }
        return voice_mapping.get(name.lower())
    
    async def speech_to_text(self, audio_content: bytes) -> dict:
        """
        Convert speech to text using ElevenLabs STT API.
        
        Args:
            audio_content: Audio file content as bytes
            
        Returns:
            Transcription result with text and metadata
        """
        try:
            if not self.client:
                raise Exception("ElevenLabs client not initialized - check API key")
            
            import io
            import tempfile
            import os
            
            print(f"🔍 Audio content size: {len(audio_content)} bytes")
            print(f"🔍 First 20 bytes: {audio_content[:20]}")
            print(f"🔍 Last 20 bytes: {audio_content[-20:]}")
            
            # Check if file is empty
            if len(audio_content) == 0:
                raise Exception("Audio file is empty!")
            
            # Check if file is too small (likely corrupted)
            if len(audio_content) < 1000:
                raise Exception(f"Audio file too small ({len(audio_content)} bytes) - likely corrupted")
            
            # Check for valid audio headers
            # WAV files should start with "RIFF" and contain "WAVE"
            if audio_content[:4] != b'RIFF':
                print(f"⚠️ Warning: File doesn't start with RIFF header. First 4 bytes: {audio_content[:4]}")
                # Try to detect format
                if audio_content[:3] == b'ID3':
                    print("🔍 Detected MP3 format")
                elif b'ftyp' in audio_content[:20]:
                    print("🔍 Detected MP4/M4A format")
                elif audio_content[:2] == b'\xff\xfb' or audio_content[:2] == b'\xff\xfa':
                    print("🔍 Detected MP3 format (MPEG header)")
                else:
                    print(f"🔍 Unknown format. First 10 bytes: {audio_content[:10]}")
            else:
                print("🔍 Detected WAV format")
            
            # Create a temporary file for the audio content
            # Use .wav format as it's most compatible with ElevenLabs STT
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_content)
                temp_file_path = temp_file.name
            
            print(f"🔍 Created temp file: {temp_file_path}")
            print(f"🔍 Temp file size: {os.path.getsize(temp_file_path)} bytes")
            
            # Try to validate the file is readable
            try:
                with open(temp_file_path, 'rb') as test_file:
                    test_content = test_file.read(100)
                    print(f"🔍 Temp file first 20 bytes: {test_content[:20]}")
            except Exception as e:
                print(f"❌ Error reading temp file: {e}")
                raise Exception(f"Temp file is not readable: {e}")
            
            try:
                # Try using the correct ElevenLabs STT API method
                with open(temp_file_path, 'rb') as audio_file:
                    # Try different API methods to find the correct one
                    try:
                        # Method 1: Direct convert
                        result = self.client.speech_to_text.convert(
                            file=audio_file,
                            model_id="scribe_v1"
                        )
                    except AttributeError:
                        # Method 2: Alternative API call
                        audio_file.seek(0)  # Reset file pointer
                        result = self.client.speech_to_text.convert(
                            audio_file,
                            model_id="scribe_v1"
                        )
                
                print(f"✅ STT Success: {result.text}")
                
                return {
                    "text": result.text,
                    "language_code": getattr(result, 'language_code', 'en'),
                    "language_probability": getattr(result, 'language_probability', 1.0),
                    "words": getattr(result, 'words', []),
                    "confidence": 0.9  # ElevenLabs doesn't provide confidence, so we estimate
                }
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    print(f"🗑️ Cleaned up temp file: {temp_file_path}")
            
        except Exception as e:
            print(f"❌ STT Error: {str(e)}")
            raise Exception(f"STT conversion failed: {str(e)}")

# Global instance
elevenlabs_client = ElevenLabsClient()
