import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

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
  (config) => {
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
