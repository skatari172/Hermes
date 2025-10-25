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

