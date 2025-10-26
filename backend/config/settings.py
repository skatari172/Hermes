import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="allow")
    
    # Firebase Configuration
    firebase_api_key: str = Field(default="", validation_alias="FIREBASE_API_KEY")
    firebase_auth_domain: str = Field(default="", validation_alias="FIREBASE_AUTH_DOMAIN")
    firebase_project_id: str = Field(default="hermes-521f9", validation_alias="FIREBASE_PROJECT_ID")
    firebase_storage_bucket: str = Field(default="", validation_alias="FIREBASE_STORAGE_BUCKET")
    firebase_messaging_sender_id: str = Field(default="", validation_alias="FIREBASE_MESSAGING_SENDER_ID")
    firebase_app_id: str = Field(default="", validation_alias="FIREBASE_APP_ID")
    
    # Google APIs
    google_maps_api_key: str = Field(default="", validation_alias="GOOGLE_MAPS_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    google_translate_api_key: Optional[str] = Field(default=None, validation_alias="GOOGLE_TRANSLATE_API_KEY")
    
    # ElevenLabs TTS
    elevenlabs_api_key: str = Field(default="", validation_alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(default="pNInz6obpgDQGcFmaJgB", validation_alias="ELEVENLABS_VOICE_ID")
    
    # Backend Configuration
    backend_host: str = Field(default="localhost", validation_alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, validation_alias="BACKEND_PORT")
    debug: bool = Field(default=True, validation_alias="DEBUG")
    
    # CORS Configuration
    cors_origins: list = Field(default=["*"], validation_alias="CORS_ORIGINS")

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

settings = get_settings()
