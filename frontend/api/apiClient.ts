import axios from 'axios';

// Dynamic backend URL detection
let BASE_URL = 'http://localhost:8000'; // Default fallback

// Auto-detect the correct backend URL
const detectBackendURL = async () => {
  const possibleURLs = [
    'http://10.127.217.215:8000',  // Your computer's actual IP
    'http://localhost:8000',        // Web browser
    'http://127.0.0.1:8000',       // Alternative localhost
    'http://10.0.2.2:8000',        // Android emulator
    'http://192.168.1.100:8000',   // Common local network
    'http://192.168.0.100:8000',   // Alternative local network
    'http://192.168.1.101:8000',   // Another common IP
    'http://192.168.0.101:8000',   // Another alternative
  ];

  for (const url of possibleURLs) {
    try {
      const response = await fetch(`${url}/health`, {
        method: 'GET',
      });
      if (response.ok) {
        console.log(`✅ Backend found at: ${url}`);
        return url;
      }
    } catch (error) {
      // Continue to next URL
    }
  }
  
  console.log('⚠️ No backend found, using default:', BASE_URL);
  return BASE_URL;
};

// Initialize the base URL
detectBackendURL().then(url => {
  BASE_URL = url;
  console.log(`🚀 Using backend URL: ${BASE_URL}`);
});

// Create axios instance - NO RESTRICTIONS
const apiClient = axios.create({
  baseURL: BASE_URL,
  // Remove timeout restrictions
  // Remove header restrictions
});

// Voice interaction API functions
export const voiceAPI = {
  // Convert text to speech
  textToSpeech: async (text: string, voiceId?: string, userId: string = 'demo_user', sessionId: string = 'demo_session') => {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('user_id', userId);
    formData.append('session_id', sessionId);
    if (voiceId) {
      formData.append('voice_id', voiceId);
    }

    const response = await apiClient.post('/api/voice/speak', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob', // For audio data
    });
    
    return response.data;
  },

  // Stream text to speech
  textToSpeechStream: async (text: string, voiceId?: string, userId: string = 'demo_user', sessionId: string = 'demo_session') => {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('user_id', userId);
    formData.append('session_id', sessionId);
    if (voiceId) {
      formData.append('voice_id', voiceId);
    }

    const response = await apiClient.post('/api/voice/speak/stream', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    return response.data;
  },

  // Voice chat (text input with audio response)
  voiceChat: async (message: string, voiceId?: string, userId: string = 'demo_user', sessionId: string = 'demo_session') => {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('user_id', userId);
    formData.append('session_id', sessionId);
    formData.append('stream_audio', 'false'); // Get audio as base64
    if (voiceId) {
      formData.append('voice_id', voiceId);
    }

    const response = await apiClient.post('/api/voice/chat', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },

  // Transcribe audio (placeholder for future implementation)
  transcribeAudio: async (audioFile: File, userId: string = 'demo_user', sessionId: string = 'demo_session') => {
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    formData.append('user_id', userId);
    formData.append('session_id', sessionId);

    const response = await apiClient.post('/api/voice/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },

  // Get available voices
  getVoices: async () => {
    const response = await apiClient.get('/api/voice/voices');
    return response.data;
  },

  // Clear conversation context
  clearContext: async (userId: string = 'demo_user', sessionId: string = 'demo_session') => {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('session_id', sessionId);

    const response = await apiClient.post('/api/voice/clear-context', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
};

export default apiClient;
