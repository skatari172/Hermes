import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Firebase Configuration
    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "hermes-521f9")
    firebase_private_key: str = os.getenv("FIREBASE_PRIVATE_KEY", "REPLACE_WITH_YOUR_FIREBASE_PRIVATE_KEY")
    firebase_client_email: str = os.getenv("FIREBASE_CLIENT_EMAIL", "REPLACE_WITH_YOUR_FIREBASE_CLIENT_EMAIL")
    firebase_private_key_id: str = os.getenv("FIREBASE_PRIVATE_KEY_ID", "REPLACE_WITH_YOUR_FIREBASE_PRIVATE_KEY_ID")
    firebase_client_id: str = os.getenv("FIREBASE_CLIENT_ID", "REPLACE_WITH_YOUR_FIREBASE_CLIENT_ID")
    firebase_auth_uri: str = os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth")
    firebase_token_uri: str = os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token")
    
    # API Configuration
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # CORS Configuration
    allowed_origins: list = ["http://localhost:3000", "http://localhost:8081", "exp://192.168.1.100:8081"]
    
    class Config:
        env_file = ".env"

settings = Settings()
