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
