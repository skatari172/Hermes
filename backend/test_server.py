#!/usr/bin/env python3
"""
Simple test server to verify basic connectivity
Run this to test if the API is working without Firebase dependencies
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Hermes Test API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Test API is working! 🎉", "status": "success"}

@app.get("/user/test")
def test_user_endpoint():
    return {"message": "User test endpoint working!", "status": "success"}

@app.post("/user/register")
def test_register(user_data: dict):
    return {
        "success": True,
        "message": "Test registration endpoint",
        "received_data": user_data
    }

if __name__ == "__main__":
    print("🧪 Starting Test API Server...")
    print("📍 Test API: http://localhost:8000")
    print("🔗 Try: http://localhost:8000/user/test")
    print("=" * 40)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
