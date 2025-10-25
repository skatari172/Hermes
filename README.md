# Hermes – AI Cultural Companion - Ayaan

An intelligent travel companion that helps you understand and document cultural experiences through AI-powered image analysis, conversation, and journaling.

## Architecture

- **Frontend**: React Native + Expo (TypeScript)
- **Backend**: FastAPI + ADK-style multi-agent system (Python)
- **AI**: Google Gemini Vision for image understanding
- **Database**: Firebase Firestore
- **Maps**: Google Maps API

## Quick Start

### Prerequisites

- Node.js (v18 or higher)
- Python 3.8+
- npm or yarn
- iOS Simulator (for iOS development)
- Git

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Hermes
```

### 2. Environment Setup

Copy the environment template and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your actual API keys:
```env
# Firebase Configuration
FIREBASE_API_KEY=your_firebase_api_key_here
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef123456

# Google APIs
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional Services
GOOGLE_TRANSLATE_API_KEY=your_translate_api_key_here
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here

# Backend Configuration
BACKEND_HOST=localhost
BACKEND_PORT=8000
DEBUG=True
```

### 3. Frontend Setup (React Native + Expo)

Navigate to the frontend directory and install dependencies:

```bash
cd frontend
npm install
```

Install additional required packages:

```bash
npm install axios expo-image-picker expo-camera expo-speech firebase
```

**Note**: If you encounter TypeScript configuration issues, ensure your `tsconfig.json` extends the correct Expo configuration:

```json
{
  "extends": "@expo/tsconfig",
  "compilerOptions": {
    "strict": true
  }
}
```

### 4. Backend Setup (FastAPI + Python)

Navigate to the backend directory and set up Python environment:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Running the Application

#### Start the Backend Server

```bash
# From the root directory
./run.sh

# Or manually:
cd backend
source venv/bin/activate
python main.py
```

The backend will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

#### Start the Frontend

```bash
cd frontend
npx expo start
```

Then:
- Press `i` to open iOS Simulator
- Press `w` to open in web browser
- Scan QR code with Expo Go app on your phone

### 6. Project Structure

```
hermes/
├── frontend/
│   ├── App.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── api/
│   │   └── apiClient.ts                # Axios wrapper for backend requests
│   ├── components/
│   │   ├── AuthInput.tsx               # Shared input for login/signup
│   │   ├── CameraPicker.tsx            # Unified camera/gallery selector
│   │   ├── ChatBubble.tsx              # Renders user/Hermes messages
│   │   ├── VoiceRecorder.tsx           # Speech-to-text input
│   │   ├── TTSPlayer.tsx               # Text-to-speech player
│   │   └── Loader.tsx                  # Small loading spinner
│   ├── screens/
│   │   ├── SignUpScreen.tsx            # Firebase email signup
│   │   ├── LoginScreen.tsx             # Firebase login
│   │   ├── ChatScreen.tsx              # Image upload + chat in one
│   │   ├── JournalScreen.tsx           # List of travel journals
│   │   └── MapScreen.tsx               # Map view for visited landmarks
│   ├── context/
│   │   ├── AuthContext.tsx             # Firebase auth context provider
│   │   └── SessionContext.tsx          # Holds chat session + memory
│   └── assets/
│       ├── icons/
│       └── demo_images/
│
├── backend/
│   ├── main.py                         # FastAPI entrypoint + ADK bus setup
│   ├── requirements.txt
│   ├── config/
│   │   ├── settings.py                 # Loads environment variables
│   │   └── logger.py                   # Centralized logging setup
│   ├── routes/
│   │   ├── photo_routes.py             # POST /api/photo — triggers PerceptionAgent
│   │   ├── chat_routes.py              # POST /api/chat — chat with Hermes
│   │   ├── end_routes.py               # POST /api/chat/end — clear memory
│   │   └── cron_routes.py              # POST /cron/daily-digest (future Twilio job)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── perception_agent.py         # Gemini Vision (image understanding + OCR)
│   │   ├── geo_agent.py                # Reverse geocoding + nearby places
│   │   ├── context_agent.py            # Merge perception + geo into narrative
│   │   ├── conversation_agent.py       # Handles dialogue + session memory
│   │   └── journal_agent.py            # Logs summaries to Firestore
│   ├── utils/
│   │   ├── bus.py                      # Lightweight pub/sub message bus
│   │   ├── gemini_client.py            # Gemini Vision/Text wrappers
│   │   ├── maps_client.py              # Google Maps API helper
│   │   ├── firestore_client.py         # Firestore database client
│   │   ├── translate_client.py         # Optional translator fallback
│   │   └── helpers.py                  # Common helper functions
│   ├── memory/
│   │   ├── session_store.py            # Stores per-user in-memory chat history
│   │   └── summarizer.py               # Updates running conversation summary
│   └── scripts/
│       ├── seed_demo_data.py           # Populate Firestore with test entries
│       └── test_event_flow.py          # Simulate full event chain
│
├── docs/
│   ├── architecture.md                 # Detailed agent flow + architecture
│   ├── technical_flow.md               # System design + sequence diagrams
│   ├── post_hackathon_plan.md
│   └── slides/
│       ├── architecture.png
│       ├── mvp_demo.png
│       └── roadmap.png
│
├── .env                                # API keys + Firebase credentials
├── README.md
├── requirements.txt                    # Backend deps root reference
└── run.sh                              # Start backend server
```

### 7. Development Workflow

1. **Backend Development**: Work in `backend/` directory with Python virtual environment activated
2. **Frontend Development**: Work in `frontend/` directory with Expo development server running
3. **API Integration**: Use `frontend/api/apiClient.ts` for backend communication
4. **Testing**: Use `backend/scripts/` for testing agent flows

### 8. Troubleshooting

#### Common Issues:

**TypeScript Configuration Error:**
```bash
# Install missing Expo TypeScript config
npm install --save-dev @expo/tsconfig
```

**iOS Folder Being Tracked:**
```bash
# Add to .gitignore
echo "ios/" >> .gitignore
git rm -r --cached ios/
git commit -m "Remove iOS folder from tracking"
```

**Python Virtual Environment:**
```bash
# If venv doesn't activate properly
python3 -m venv venv --clear
source venv/bin/activate
pip install -r requirements.txt
```

**Expo Dependencies:**
```bash
# Clear cache and reinstall
npx expo install --fix
```

### 9. API Keys Setup

You'll need to obtain API keys from:

1. **Firebase**: Create a project at [Firebase Console](https://console.firebase.google.com/)
2. **Google Maps**: Get API key from [Google Cloud Console](https://console.cloud.google.com/)
3. **Gemini**: Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
4. **Optional**: Google Translate, Twilio for future features

### 10. Next Steps

- See `docs/architecture.md` for detailed system design
- Check `docs/technical_flow.md` for API documentation
- Review `docs/post_hackathon_plan.md` for future roadmap

## Contributing

1. Create a feature branch
2. Make your changes
3. Test both frontend and backend
4. Submit a pull request

## Support

For questions or issues, check the documentation in the `docs/` folder or create an issue in the repository.
