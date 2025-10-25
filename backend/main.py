"""
FastAPI entrypoint for Hermes AI Cultural Companion.
Sets up the server and includes all routes.
"""

from config.settings import get_settings
settings = get_settings()

# FastAPI setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Hermes AI Cultural Companion",
    description="An intelligent travel companion for cultural experiences",
    version="1.0.0"
)

# Add CORS middleware - ALLOW EVERYTHING
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Disable credentials
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Hermes AI Cultural Companion",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Hermes AI Cultural Companion"
    }

# Import and include the voice routes
from routes.voice_routes import router as voice_router
app.include_router(voice_router)

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Hermes AI Cultural Companion on {settings.backend_host}:{settings.backend_port}")
    print(f"📚 API docs available at http://{settings.backend_host}:{settings.backend_port}/docs")
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    )


from fastapi import FastAPI
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
