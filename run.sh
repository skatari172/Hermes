#!/bin/bash

# Hermes AI Cultural Companion - Startup Script
# Checks prerequisites and starts both backend and frontend

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Hermes AI Cultural Companion...${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check Node.js
if ! command_exists node; then
    echo -e "${RED}❌ Node.js is not installed. Please install Node.js v18 or higher.${NC}"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}❌ Node.js version $NODE_VERSION is too old. Please install Node.js v18 or higher.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js $(node --version)${NC}"

# Check Python
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env and fill in your API keys.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ .env file found${NC}"

# Check if ports are available
if port_in_use 8000; then
    echo -e "${RED}❌ Port 8000 is already in use. Please stop the process using this port.${NC}"
    exit 1
fi

if port_in_use 8081; then
    echo -e "${RED}❌ Port 8081 is already in use. Please stop the process using this port.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites check passed!${NC}"
echo ""

# Function to start backend
start_backend() {
    echo -e "${BLUE}🐍 Starting FastAPI backend...${NC}"
    cd backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}📦 Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
    source venv/bin/activate
    
    # Install dependencies if needed
    if [ ! -f "venv/pyvenv.cfg" ] || [ requirements.txt -nt venv/pyvenv.cfg ]; then
        echo -e "${YELLOW}📥 Installing Python dependencies...${NC}"
        pip install -r requirements.txt
    fi
    
    # Start the server
    echo -e "${GREEN}🌟 Starting FastAPI server on http://localhost:8000${NC}"
    echo -e "${GREEN}📚 API docs available at http://localhost:8000/docs${NC}"
    python main.py &
    BACKEND_PID=$!
    cd ..
}

# Function to start frontend
start_frontend() {
    echo -e "${BLUE}📱 Starting React Native frontend...${NC}"
    cd frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
        npm install
    fi
    
    # Start Expo development server in foreground
    echo -e "${GREEN}🌟 Starting Expo development server...${NC}"
    echo -e "${GREEN}📱 Press 'i' for iOS Simulator, 'w' for web, or scan QR code with Expo Go${NC}"
    echo -e "${GREEN}📱 Press Ctrl+C to stop both backend and frontend${NC}"
    echo ""
    npx expo start --tunnel
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down backend...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ Backend stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
start_backend
sleep 2  # Give backend time to start

echo ""
echo -e "${GREEN}🎉 Backend is running!${NC}"
echo -e "${BLUE}Backend: http://localhost:8000${NC}"
echo -e "${BLUE}API docs: http://localhost:8000/docs${NC}"
echo ""

# Start frontend in foreground (this will block until user exits)
start_frontend
