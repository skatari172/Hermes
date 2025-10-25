"""
ElevenLabs TTS API client for voice synthesis.
Handles text-to-speech conversion using ElevenLabs API.
"""

import os
import io
import asyncio
from typing import Optional, AsyncGenerator
from elevenlabs import Voice, VoiceSettings, generate, stream
from elevenlabs.client import ElevenLabs
import httpx
from config.settings import get_settings

settings = get_settings()

class ElevenLabsClient:
    """Client for ElevenLabs Text-to-Speech API."""
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not found in environment variables")
        
        self.client = ElevenLabs(api_key=self.api_key)
        
        # Default voice settings for Hermes
        self.default_voice = Voice(
            voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice (default)
            settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.8,
                style=0.0,
                use_speaker_boost=True
            )
        )
    
    async def text_to_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model: str = "eleven_monolingual_v1"
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
            voice = self.default_voice
            if voice_id:
                voice = Voice(voice_id=voice_id)
            
            # Generate audio
            audio = generate(
                text=text,
                voice=voice,
                model=model,
                api_key=self.api_key
            )
            
            return audio
            
        except Exception as e:
            raise Exception(f"TTS generation failed: {str(e)}")
    
    async def stream_text_to_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model: str = "eleven_monolingual_v1"
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
            voice = self.default_voice
            if voice_id:
                voice = Voice(voice_id=voice_id)
            
            # Stream audio generation
            audio_stream = stream(
                text=text,
                voice=voice,
                model=model,
                api_key=self.api_key
            )
            
            for chunk in audio_stream:
                yield chunk
                
        except Exception as e:
            raise Exception(f"TTS streaming failed: {str(e)}")
    
    async def get_available_voices(self) -> list:
        """Get list of available voices from ElevenLabs."""
        try:
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

# Global instance
elevenlabs_client = ElevenLabsClient()
