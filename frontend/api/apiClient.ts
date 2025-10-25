import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { auth } from '../config/firebase';

// Create axios instance with base configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL || 'http://10.127.199.242:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    try {
      // Check if user is authenticated with Firebase
      const currentUser = auth.currentUser;
      if (currentUser) {
        // Get the Firebase ID token
        const token = await currentUser.getIdToken();
        config.headers.Authorization = `Bearer ${token}`;
      } else {
        // Fallback to device-specific demo token for unauthenticated users
        let demoUserId = await AsyncStorage.getItem('demo_user_id');
        if (!demoUserId) {
          demoUserId = Math.random().toString(36).substring(2, 15);
          await AsyncStorage.setItem('demo_user_id', demoUserId);
        }
        config.headers.Authorization = `Bearer demo_device_${demoUserId}`;
      }
    } catch (error) {
      console.error('Error getting auth token:', error);
      // Fallback to demo mode if Firebase fails
      try {
        let demoUserId = await AsyncStorage.getItem('demo_user_id');
        if (!demoUserId) {
          demoUserId = Math.random().toString(36).substring(2, 15);
          await AsyncStorage.setItem('demo_user_id', demoUserId);
        }
        config.headers.Authorization = `Bearer demo_device_${demoUserId}`;
      } catch (storageError) {
        console.error('Error with AsyncStorage:', storageError);
        // Final fallback - use random session ID
        config.headers.Authorization = `Bearer demo_device_${Math.random().toString(36).substring(2, 15)}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth API functions
export const authAPI = {
  register: (userData: {
    first_name: string;
    last_name: string;
    email: string;
    password: string;
  }) => {
    return apiClient.post('/user/register', userData);
  },
  
  login: (credentials: {
    email: string;
    password: string;
  }) => {
    return apiClient.post('/user/login', credentials);
  },
};

// User API functions
export const userAPI = {
  getProfile: (token: string) => {
    return apiClient.get('/user/profile', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },
  
  updateProfile: (profileData: any, token: string) => {
    return apiClient.put('/user/profile', profileData, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },
  
  deleteProfile: (token: string) => {
    return apiClient.delete('/user/profile', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },
};

export default apiClient;
