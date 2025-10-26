import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ScrollView, KeyboardAvoidingView, Platform, StatusBar, ActivityIndicator, Linking, NativeModules } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CameraButton, MicButton, TextInput } from '../components/homecomponents';
import * as FileSystem from 'expo-file-system';
import { Audio } from 'expo-av';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import { useFocusEffect } from '@react-navigation/native';
import apiClient from '../../api/apiClient';
import { journalAPI } from '../../api/apiClient';
import { useAuth } from '../../contexts/AuthContext';
import { PorcupineManager, BuiltInKeywords } from '@picovoice/porcupine-react-native';
import { VoiceProcessor } from '@picovoice/react-native-voice-processor';

export default function HomeScreen() {
  const [messages, setMessages] = useState<Array<{id: string, text: string, timestamp: Date, isUser: boolean, imageUri?: string}>>([]);
  const [inputText, setInputText] = useState('');
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<{latitude: number, longitude: number} | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  // Ref to hold currently playing sound and temp file uri so we can stop/cleanup from UI
  const currentSoundRef = useRef<any>(null);
  const currentSoundFileUriRef = useRef<string | null>(null);
  
  // Auto-camera state
  const [cameraShownForCurrentFocus, setCameraShownForCurrentFocus] = useState(false);
  const [cameraPermissionStatus, setCameraPermissionStatus] = useState<ImagePicker.PermissionStatus | null>(null);
  
  // TTS speed control
  const [ttsSpeed, setTtsSpeed] = useState(1.5); // Default to 1.5x speed (50% faster)

  // Wake word detection state
  const [isListeningForWakeWord, setIsListeningForWakeWord] = useState(false);
  const [wakeWordDetected, setWakeWordDetected] = useState(false);
  const [wakeWordStatusMessage, setWakeWordStatusMessage] = useState<string | null>(null);
  const micButtonRef = useRef<any>(null);
  const porcupineRef = useRef<any>(null);

  // Porcupine access key - Get from https://console.picovoice.ai/
  // Set EXPO_PUBLIC_PORCUPINE_ACCESS_KEY in your environment or replace the placeholder below
  const PORCUPINE_ACCESS_KEY = process.env.EXPO_PUBLIC_PORCUPINE_ACCESS_KEY || 'YOUR_ACCESS_KEY_HERE';

  // Request location permission and get current location
  useEffect(() => {
    (async () => {
      try {
        let { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          console.log('Location permission denied');
          return;
        }
        
        let location = await Location.getCurrentPositionAsync({});
        setCurrentLocation({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude
        });
        console.log('📍 Current location set:', location.coords.latitude, location.coords.longitude);
      } catch (error) {
        console.error('Error getting location:', error);
      }
    })();
  }, []);

  // Initialize Porcupine wake word detection
  useEffect(() => {
    let porcupineManager: any = null;

    const initPorcupine = async () => {
      try {
        console.log('🎯 Initializing Porcupine wake word detection...');
        setWakeWordStatusMessage(null);

        if (PORCUPINE_ACCESS_KEY === 'YOUR_ACCESS_KEY_HERE' || !process.env.EXPO_PUBLIC_PORCUPINE_ACCESS_KEY) {
          const message = 'Add a Porcupine Access Key to enable wake word detection.';
          console.log('⚠️', message);
          setWakeWordStatusMessage(message);
          setIsListeningForWakeWord(false);
          return;
        }

        if (!NativeModules?.PvPorcupine) {
          const message = 'Wake word detection needs a custom Expo dev build that bundles the Picovoice native module. Expo Go does not include it by default.';
          console.log('⚠️', message);
          setWakeWordStatusMessage(message);
          setIsListeningForWakeWord(false);
          return;
        }

        if (!VoiceProcessor?.instance) {
          const message = 'VoiceProcessor native module is unavailable. Build a custom dev client to continue.';
          console.log('⚠️', message);
          setWakeWordStatusMessage(message);
          setIsListeningForWakeWord(false);
          return;
        }

        if (!PorcupineManager || !PorcupineManager.fromBuiltInKeywords) {
          const message = 'PorcupineManager API is unavailable. Verify @picovoice/porcupine-react-native is installed and autolinked.';
          console.error('❌', message);
          setWakeWordStatusMessage(message);
          setIsListeningForWakeWord(false);
          return;
        }

        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          console.log('❌ Microphone permission denied for wake word detection');
          Alert.alert(
            'Microphone Permission Required',
            'Enable microphone access to use "Hey Hermes" wake word detection',
            [{ text: 'OK' }]
          );
          setWakeWordStatusMessage('Microphone permission denied');
          return;
        }

        const detectionCallback = async (keywordIndex: number) => {
          console.log('✅ Wake word detected! Index:', keywordIndex);
          await handleWakeWordTriggered();
        };

        const errorCallback = (error: any) => {
          console.error('❌ Porcupine error:', error);
          setWakeWordStatusMessage(error?.message ?? 'Porcupine error occurred');
        };

        porcupineManager = await PorcupineManager.fromBuiltInKeywords(
          PORCUPINE_ACCESS_KEY,
          [BuiltInKeywords.HEY_GOOGLE],
          detectionCallback,
          errorCallback
        );
        console.log('✅ Using built-in "Hey Google" wake word');

        porcupineRef.current = porcupineManager;

        await porcupineManager.start();

        setIsListeningForWakeWord(true);
        setWakeWordStatusMessage(null);
        console.log('👂 Porcupine listening for "Hey Hermes"...');

      } catch (error: any) {
        console.error('❌ Porcupine initialization error:', error);

        if (error?.message?.includes('AccessKey')) {
          const message = 'Porcupine Access Key invalid or missing. Update EXPO_PUBLIC_PORCUPINE_ACCESS_KEY and restart.';
          setWakeWordStatusMessage(message);
        } else if (error?.message?.includes('Device is not supported') || error?.message?.includes('null is not an object')) {
          const message = 'This build does not include the Porcupine native module. Create a custom dev client with "npx expo run:ios" or EAS Build.';
          setWakeWordStatusMessage(message);
        } else {
          setWakeWordStatusMessage(error?.message || 'Porcupine initialization failed.');
        }

        setIsListeningForWakeWord(false);
      }
    };

    if (Platform.OS === 'ios') {
      initPorcupine();
    } else {
      const message = 'Wake word detection currently enabled only on iOS builds.';
      console.log('⚠️', message);
      setWakeWordStatusMessage(message);
    }

    return () => {
      if (porcupineRef.current) {
        console.log('🛑 Stopping Porcupine...');
        porcupineRef.current.stop().catch((e: any) => console.error('Stop error:', e));
        porcupineRef.current.delete().catch((e: any) => console.error('Delete error:', e));
        porcupineRef.current = null;
        setIsListeningForWakeWord(false);
      }
    };
  }, [PORCUPINE_ACCESS_KEY]);

  // Handle wake word triggered
  const handleWakeWordTriggered = async () => {
    try {
      console.log('🎯 Wake word triggered - starting voice recording');
      setWakeWordDetected(true);

      // Provide visual/audio feedback
      const wakeMessage = {
        id: Date.now().toString(),
        text: '👋 Hey! I\'m listening...',
        timestamp: new Date(),
        isUser: false
      };
      setMessages(prev => [...prev, wakeMessage]);

      // Trigger the MicButton to start recording
      // Note: You'll need to expose a startRecording method in MicButton component
      if (micButtonRef.current?.startRecording) {
        await micButtonRef.current.startRecording();
      } else {
        // Fallback: Show alert to tap microphone
        Alert.alert(
          '👋 Hey there!',
          'Hermes is ready to listen. Tap the microphone to start speaking.',
          [{ text: 'OK' }]
        );
      }

      // Reset wake word detected after delay
      setTimeout(() => {
        setWakeWordDetected(false);
      }, 3000);

    } catch (error) {
      console.error('Error handling wake word trigger:', error);
      setWakeWordDetected(false);
    }
  };


  const { user } = useAuth();

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages]);

  // Check camera permission on mount
  useEffect(() => {
    (async () => {
      const { status } = await ImagePicker.getCameraPermissionsAsync();
      setCameraPermissionStatus(status);
    })();
  }, []);

  // Auto-camera logic when screen is focused
  useFocusEffect(
    React.useCallback(() => {
      // Reset camera shown flag when screen is focused
      setCameraShownForCurrentFocus(false);
      
      // Use a timeout to ensure the state update has been processed
      const timer = setTimeout(() => {
        // Check if we should show camera automatically
        const shouldShowCamera = 
          messages.length === 0 && 
          !inputText.trim();
        
        if (shouldShowCamera) {
          handleAutoCamera();
        }
      }, 100);
      
      return () => clearTimeout(timer);
    }, [messages.length, inputText])
  );


  // Helper function to check if timestamp should be shown
  const shouldShowTimestamp = (currentIndex: number) => {
    if (currentIndex === 0) return true; // Always show for first message
    
    const currentMessage = messages[currentIndex];
    const previousMessage = messages[currentIndex - 1];
    
    // Show timestamp if time is different (compare by minutes)
    const currentTime = new Date(currentMessage.timestamp);
    const previousTime = new Date(previousMessage.timestamp);
    
    return currentTime.getMinutes() !== previousTime.getMinutes() || 
           currentTime.getHours() !== previousTime.getHours();
  };

  // Stop any currently playing TTS and cleanup temp file
  const stopCurrentTts = async () => {
    try {
      if (currentSoundRef.current) {
        try { await currentSoundRef.current.stopAsync(); } catch (e) {}
        try { await currentSoundRef.current.unloadAsync(); } catch (e) {}
        currentSoundRef.current = null;
      }
      if (currentSoundFileUriRef.current) {
        try { await FileSystem.deleteAsync(currentSoundFileUriRef.current, { idempotent: true }); } catch (e) {}
        currentSoundFileUriRef.current = null;
      }
    } catch (e) {
      console.error('Stop TTS error:', e);
    }
  };

  // Play base64 mp3 audio (handles data URL fallback and temp file approach)
  const playBase64Audio = async (audioData: string) => {
    try {
      // Stop any previously playing audio first
      await stopCurrentTts();

      if (!FileSystem) {
        // Fallback: use data URL directly
        const dataUrl = `data:audio/mp3;base64,${audioData}`;
        const { sound } = await Audio.Sound.createAsync({ uri: dataUrl }, { shouldPlay: true });
        currentSoundRef.current = sound;
        sound.setOnPlaybackStatusUpdate((status: any) => {
          if (status.isLoaded && status.didJustFinish) {
            try { sound.unloadAsync(); } catch (e) {}
            currentSoundRef.current = null;
          }
        });
        return;
      }

      const fileName = `tts_audio_${Date.now()}.mp3`;
      const fileUri = `file:///tmp/${fileName}`;
      currentSoundFileUriRef.current = fileUri;

      await FileSystem.writeAsStringAsync(fileUri, audioData, {
        encoding: 'base64' as any,
      });

      const { sound } = await Audio.Sound.createAsync({ uri: fileUri }, { shouldPlay: true });
      currentSoundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status: any) => {
        if (status.isLoaded && status.didJustFinish) {
          try { sound.unloadAsync(); } catch (e) {}
          try { FileSystem.deleteAsync(fileUri, { idempotent: true }); } catch (e) {}
          currentSoundRef.current = null;
          currentSoundFileUriRef.current = null;
        }
      });
    } catch (e) {
      console.error('playBase64Audio error:', e);
    }
  };

  // Auto-camera handler
  const handleAutoCamera = async () => {
    // Mark that we've shown the camera for this focus to prevent re-triggering
    setCameraShownForCurrentFocus(true);
    
    // Check current permission status
    const { status } = await ImagePicker.getCameraPermissionsAsync();
    setCameraPermissionStatus(status);
    
    if (status === 'granted') {
      // Permission granted, launch camera directly
      launchCamera();
    } else if (status === 'undetermined') {
      // Request permission
      const { status: newStatus } = await ImagePicker.requestCameraPermissionsAsync();
      setCameraPermissionStatus(newStatus);
      
      if (newStatus === 'granted') {
        launchCamera();
      } else {
        // Permission denied, show alert
        Alert.alert(
          'Camera Permission Required',
          'Camera permission is needed to take photos. Please grant permission to use this feature.',
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Open Settings', onPress: () => Linking.openSettings() }
          ]
        );
      }
    } else {
      // Permission permanently denied, show settings alert
      Alert.alert(
        'Camera Permission Denied',
        'Camera permission has been permanently denied. Please enable it in Settings to use this feature.',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Open Settings', onPress: () => Linking.openSettings() }
        ]
      );
    }
  };

  // Launch camera function
  const launchCamera = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 1,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const source = result.assets[0].uri;
        console.log('Auto-camera image captured:', source);
        handleImageCaptured(source);
      }
    } catch (error) {
      console.error('Auto-camera error:', error);
    }
  };

  const handleGenerateJournal = async () => {
    try {
      // Use the same Bearer token as in your curl command
      const token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjdlYTA5ZDA1NzI2MmU2M2U2MmZmNzNmMDNlMDRhZDI5ZDg5Zjg5MmEiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiTmljayBHb256YWxleiIsImlzcyI6Imh0dHBzOi8vc2VjdXJldG9rZW4uZ29vZ2xlLmNvbS9oZXJtZXMtNTIxZjkiLCJhdWQiOiJoZXJtZXMtNTIxZjkiLCJhdXRoX3RpbWUiOjE3NjE0MjUxMzQsInVzZXJfaWQiOiI0aHlKcVNYY09pZTJVbExFdFc3TmNYYlNheEEzIiwic3ViIjoiNGh5SnFTWGNPaWUyVWxMRXRXN05jWGJTYXhBMyIsImlhdCI6MTc2MTQyNTEzNCwiZXhwIjoxNzYxNDI4NzM0LCJlbWFpbCI6ImJvYm9yYW4xNEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsiYm9ib3JhbjE0QGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.zsjYTwHTGmIQpCGOj_PmbsFB51f7idcAfUQSqvA76ba7XwD8E7BBwTCmcGjEqnTpg65YkXGQZxcobeuYXapixJTO7ID0O0gmaMyzpO3-IXEqSflred9V1HSAYbADi-ACbvoVufDhq0pTsyHiNaGA0GIj64GF5-Eh9bi99hZAZPsfdWqCeGKshW7pLgb_oFrNjrECrxsGGx3CsfBKrstO9TrFRVS-vY9yjXUqxzZPYf6uckAEjtqfKnzAdM8iY_N7xqsnyVQgfJDnRj5AVD8fePkb3TA-Rr7qqJrGAKOSyXScCCHTNivGAecDXUvcmBBNzR3pNnkXbs-O51MvwPsc1A";
      
      // Show loading alert
      Alert.alert('Generating Journal', 'Creating journal entry from your conversation...');
      
      // Call the generate-latest endpoint
      const res = await journalAPI.generateFromLatest(token);
      const data = res.data;
      
      if (data && data.success) {
        // Show the generated journal entry
        Alert.alert(
          'Journal Entry Generated!', 
          `Your journal entry has been created:\n\n${data.diary_entry?.substring(0, 200)}...`,
          [
            { text: 'OK' },
            { 
              text: 'View Full Entry', 
              onPress: () => {
                Alert.alert('Full Journal Entry', data.diary_entry || 'No content available');
              }
            }
          ]
        );
      } else {
        Alert.alert('Generation Failed', data?.message || 'Failed to generate journal entry. Make sure you have had a conversation first.');
      }
    } catch (e: any) {
      console.error('Generate journal failed:', e?.response?.data || e?.message || e);
      const errorMessage = e?.response?.data?.message || e?.message || 'Failed to generate journal entry.';
      Alert.alert('Error', errorMessage);
    }
  };

  const handleSubmitMessage = async () => {
    if (inputText.trim()) {
      const userMessage = {
        id: Date.now().toString(),
        text: inputText.trim(),
        timestamp: new Date(),
        isUser: true
      };
      setMessages(prev => [...prev, userMessage]);
      const messageText = inputText.trim();
      setInputText('');
      setIsLoading(true);

      try {
        // Use centralized apiClient (baseURL resolved dynamically)

        // Send message to backend using apiClient with automatic auth
  const formData = new FormData();
  formData.append('user_message', messageText);
  formData.append('session_id', 'demo_session');

        const response = await apiClient.post('/api/chat/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        if (response.status === 200) {
          const result = response.data;
          if (result.status === 'success') {
            // Add bot response to messages
            const botMessage = {
              id: (Date.now() + 1).toString(),
              text: result.response,
              timestamp: new Date(),
              isUser: false
            };
            setMessages(prev => [...prev, botMessage]);

            // Trigger TTS for bot response if enabled
            if (ttsEnabled) {
              handleTtsForMessage(result.response);
            }

            // Handle TTS if enabled and audio data is available
            console.log('TTS Debug: ttsEnabled =', ttsEnabled);
            console.log('TTS Debug: result.tts_audio_data exists =', !!result.tts_audio_data);
            console.log('TTS Debug: result.tts_audio_data length =', result.tts_audio_data?.length || 0);
            
            if (ttsEnabled && result.tts_audio_data) {
              try {
                await playBase64Audio(result.tts_audio_data);
              } catch (error) {
                console.error('TTS Debug: TTS playback error:', error);
              }
            } else {
              console.log('TTS Debug: TTS not triggered - ttsEnabled:', ttsEnabled, 'audioData exists:', !!result.tts_audio_data);
            }
          } else {
            // Add error message
            const errorMessage = {
              id: (Date.now() + 1).toString(),
              text: result.message || 'Sorry, I encountered an error.',
              timestamp: new Date(),
              isUser: false
            };
            setMessages(prev => [...prev, errorMessage]);
          }
        } else {
          // Add error message for network issues
          const errorMessage = {
            id: (Date.now() + 1).toString(),
            text: 'Sorry, I cannot connect to the server right now.',
            timestamp: new Date(),
            isUser: false
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      } catch (error) {
        console.error('Chat error:', error);
        // Add error message
        const errorMessage = {
          id: (Date.now() + 1).toString(),
          text: 'Sorry, something went wrong. Please try again.',
          timestamp: new Date(),
          isUser: false
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleImageCaptured = async (imageUri: string) => {
    // Add user's image message to chat
    const newMessage = {
      id: Date.now().toString(),
      text: '',
      timestamp: new Date(),
      isUser: true,
      imageUri: imageUri
    };
    setMessages(prev => [...prev, newMessage]);
    setIsLoading(true);

    try {
      console.log('📤 Sending image to Hermes backend...');
      
      // Create FormData for image upload
      const formData = new FormData();
      // Backend expects field name 'image_file'
      formData.append('image_file', {
        uri: imageUri,
        type: 'image/jpeg',
        name: 'image.jpg',
      } as any);
      formData.append('session_id', 'demo_session');
      
      // Add current location if available
      if (currentLocation) {
        formData.append('user_latitude', currentLocation.latitude.toString());
        formData.append('user_longitude', currentLocation.longitude.toString());
        console.log('📍 Including user location:', currentLocation.latitude, currentLocation.longitude);
      }

      console.log('📤 Sending image to Hermes backend via apiClient /api/upload/image');

      // Send image to backend for processing using centralized apiClient
      const response = await apiClient.post('/api/image/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response && response.status === 200) {
        const result = response.data;
        console.log('📥 Hermes response:', result);
        
        if (result.status === 'success') {
          // Add Hermes response to chat
          const hermesMessage = {
            id: (Date.now() + 1).toString(),
            text: result.data.response.text,
            timestamp: new Date(),
            isUser: false
          };
          setMessages(prev => [...prev, hermesMessage]);

          // Handle TTS if enabled and audio data is available
          if (ttsEnabled && result.data.response.tts_audio_data) {
            try {
              await playBase64Audio(result.data.response.tts_audio_data);
            } catch (error) {
              console.error('TTS playback error:', error);
            }
          }
        } else {
          // Add error message
          const errorMessage = {
            id: (Date.now() + 1).toString(),
            text: result.message || 'Sorry, I encountered an error processing your image.',
            timestamp: new Date(),
            isUser: false
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      } else {
        // Add error message for network issues
        const errorMessage = {
          id: (Date.now() + 1).toString(),
          text: 'Sorry, I cannot connect to the server right now.',
          timestamp: new Date(),
          isUser: false
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Image processing error:', error);
      // Add error message
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, something went wrong processing your image. Please try again.',
        timestamp: new Date(),
        isUser: false
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAudioRecorded = (audioUri: string) => {
    const newMessage = {
      id: Date.now().toString(),
      text: '🎤 Audio message recorded',
      timestamp: new Date(),
      isUser: true
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleTranscriptionComplete = async (transcribedText: string) => {
    // Put the transcribed text into the text input
    setInputText(transcribedText);
    
    // Auto-send the message if there's transcribed text
    if (transcribedText.trim()) {
      // Use the same logic as handleSubmitMessage but with the transcribed text
      const userMessage = {
        id: Date.now().toString(),
        text: transcribedText.trim(),
        timestamp: new Date(),
        isUser: true
      };
      setMessages(prev => [...prev, userMessage]);
      setInputText(''); // Clear the input
  
      try {
        // Use centralized apiClient (baseURL resolved dynamically)
  const formData = new FormData();
  formData.append('user_message', transcribedText.trim());
  formData.append('session_id', 'demo_session');

        const response = await apiClient.post('/api/chat/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
  
        if (response.status === 200) {
          const result = response.data;
          if (result.status === 'success') {
            // Add bot response to messages
            const botMessage = {
              id: (Date.now() + 1).toString(),
              text: result.response,
              timestamp: new Date(),
              isUser: false
            };
            setMessages(prev => [...prev, botMessage]);
  
            // Trigger TTS for bot response if enabled
            if (ttsEnabled) {
              handleTtsForMessage(result.response);
            }

            // Handle TTS if enabled and audio data is available
            console.log('TTS Debug: ttsEnabled =', ttsEnabled);
            console.log('TTS Debug: result.tts_audio_data exists =', !!result.tts_audio_data);
            console.log('TTS Debug: result.tts_audio_data length =', result.tts_audio_data?.length || 0);
            
            if (ttsEnabled && result.tts_audio_data) {
              try {
                await playBase64Audio(result.tts_audio_data);
              } catch (error) {
                console.error('TTS Debug: TTS playback error:', error);
              }
            } else {
              console.log('TTS Debug: TTS not triggered - ttsEnabled:', ttsEnabled, 'audioData exists:', !!result.tts_audio_data);
            }
          } else {
            // Add error message
            const errorMessage = {
              id: (Date.now() + 1).toString(),
              text: result.message || 'Sorry, I encountered an error.',
              timestamp: new Date(),
              isUser: false
            };
            setMessages(prev => [...prev, errorMessage]);
          }
        } else {
          // Add error message for network issues
          const errorMessage = {
            id: (Date.now() + 1).toString(),
            text: 'Sorry, I cannot connect to the server right now.',
            timestamp: new Date(),
            isUser: false
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      } catch (error) {
        console.error('Auto-send error:', error);
        // Add error message
        const errorMessage = {
          id: (Date.now() + 1).toString(),
          text: 'Sorry, something went wrong. Please try again.',
          timestamp: new Date(),
          isUser: false
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    }
  };

  const handleTtsForMessage = async (messageText: string) => {
    if (ttsEnabled && messageText) {
      try {
        // Use centralized apiClient to call TTS endpoint
        const formData = new FormData();
        formData.append('text', messageText);
        formData.append('session_id', 'demo_session');
        formData.append('voice_id', 'b7OWsPurC81KeahWq9j7');
        formData.append('speed', ttsSpeed.toString());

        const response = await apiClient.post('/api/voice/speak', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        if (response && response.status === 200) {
          const result = response.data;
          if (result.status === 'success' && result.audio_data) {
            // Use centralized player to play returned base64 audio
            await playBase64Audio(result.audio_data);
          }
        }
      } catch (error) {
        console.error('TTS error:', error);
      }
    }
  };


  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />
      
      {/* Top Banner */}
      <View style={styles.topBanner}>
        <View style={styles.headerContent}>
          {/* Hermes perfectly centered */}
          <Text style={styles.hermesTitleAbsolute}>Hermes</Text>

          <View style={styles.headerRightContainer}>
            {/* Wake word indicator */}
            {Platform.OS === 'ios' && (
              wakeWordStatusMessage ? (
                <TouchableOpacity
                  style={styles.wakeWordErrorIndicator}
                  onPress={() =>
                    Alert.alert(
                      'Wake Word Disabled',
                      wakeWordStatusMessage,
                      [{ text: 'Got it' }]
                    )
                  }
                  accessibilityRole="button"
                  accessibilityLabel="Wake word unavailable"
                >
                  <Ionicons name="alert-circle-outline" size={16} color="#F87171" />
                  <Text style={styles.wakeWordErrorText}>Wake word off</Text>
                </TouchableOpacity>
              ) : (
                isListeningForWakeWord && (
                  <View style={styles.wakeWordIndicator}>
                    <View style={[styles.pulseIndicator, wakeWordDetected && styles.pulseActive]} />
                    <Ionicons name="mic-outline" size={14} color={wakeWordDetected ? '#10B981' : '#01AFD1'} />
                    <Text style={[styles.wakeWordText, wakeWordDetected && styles.wakeWordTextActive]}>
                      {wakeWordDetected ? 'Listening...' : 'Hey Google'}
                    </Text>
                  </View>
                )
              )
            )}
            
            {/* TTS Toggle */}
            <TouchableOpacity
              style={[styles.ttsToggle, ttsEnabled && styles.ttsToggleActive]}
              onPress={() => setTtsEnabled(!ttsEnabled)}
              accessibilityLabel="Toggle TTS"
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Ionicons
                name="volume-high"
                size={20}
                color={ttsEnabled ? '#FFFFFF' : '#01AFD1'}
              />
            </TouchableOpacity>
          </View>
        </View>
      </View>

      <KeyboardAvoidingView 
        style={styles.keyboardContainer} 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Messages Area */}
      <ScrollView style={styles.messagesContainer} showsVerticalScrollIndicator={false}>
        {messages.map((message, index) => (
          <View key={message.id} style={styles.messageContainer}>
            {message.imageUri && (
              <View style={[
                styles.imageMessageContainer,
                message.isUser ? styles.userImageContainer : styles.botImageContainer
              ]}>
                <Image source={{ uri: message.imageUri }} style={styles.messageImage} />
              </View>
            )}
            {message.text && (
              <View style={[
                styles.messageBubble,
                message.isUser ? styles.userMessage : styles.botMessage
              ]}>
                <Text style={[
                  styles.messageText,
                  message.isUser ? styles.userMessageText : styles.botMessageText
                ]}>
                  {message.text}
                </Text>
              </View>
            )}
            {shouldShowTimestamp(index) && (
              <Text style={[
                styles.timestamp,
                message.isUser ? styles.timestampRight : styles.timestampLeft
              ]}>
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </Text>
            )}
            {!message.isUser && message.text && (
              <View style={styles.reactionContainer}>
                <TouchableOpacity style={styles.reactionButton}>
                  <Ionicons name="thumbs-up-outline" size={16} color="#043263" />
                </TouchableOpacity>
                <TouchableOpacity style={styles.reactionButton}>
                  <Ionicons name="thumbs-down-outline" size={16} color="#043263" />
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.reactionButton}
                  onPress={() => { (async () => { try { await stopCurrentTts(); } catch(e){console.error(e);} })(); }}
                >
                  <Ionicons name="volume-high-outline" size={16} color="#043263" />
                </TouchableOpacity>
                <TouchableOpacity style={styles.reactionButton}>
                  <Ionicons name="refresh-outline" size={16} color="#043263" />
                </TouchableOpacity>
              </View>
            )}
          </View>
        ))}
        
        {/* Loading Indicator */}
        {isLoading && (
          <View style={styles.messageContainer}>
            <View style={[styles.messageBubble, styles.botMessage, styles.loadingMessage]}>
              <ActivityIndicator size="small" color="#01AFD1" />
            </View>
          </View>
        )}
      </ScrollView>

      {/* Input Area */}
      <View style={styles.inputContainer}>
        <CameraButton onImageCaptured={handleImageCaptured} />
        <TextInput
          value={inputText}
          onChangeText={setInputText}
          onSubmit={handleSubmitMessage}
          placeholder="Type a message.."
          maxLength={500}
        />
        <MicButton 
          ref={micButtonRef}
          onAudioRecorded={handleAudioRecorded} 
          onTranscriptionComplete={handleTranscriptionComplete}
        />
      </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#E5ECFF',
  },
  topBanner: {
    backgroundColor: '#FFFFFF',
    paddingTop: Platform.OS === 'ios' ? 50 : 30,
    paddingBottom: 15,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5ECFF',
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    padding: 8,
  },
  upgradeButton: {
    backgroundColor: '#E5ECFF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  upgradeText: {
    color: '#01AFD1',
    fontSize: 14,
    fontWeight: '500',
  },
  headerRightContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  centerHeader: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingLeft: 40,
  },
  hermesTitle: {
    color: '#01AFD1',
    fontSize: 18,
    fontWeight: '600',
    marginRight: 8,
  },
  ttsToggle: {
    padding: 8,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: '#E5ECFF',
  },
  ttsToggleActive: {
    backgroundColor: '#01AFD1',
  },
  ttsToggleCentered: {
    padding: 6,
    borderRadius: 20,
    backgroundColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
  },
  ttsToggleActiveCentered: {
    backgroundColor: '#01AFD1',
  },
  leftSpacer: {
    width: 40,
  },
  hermesTitleAbsolute: {
    position: 'absolute',
    left: 0,
    right: 0,
    textAlign: 'center',
    color: '#01AFD1',
    fontSize: 18,
    fontWeight: '600',
    zIndex: 0,
    // Allow touches to pass through the centered title so right/left controls remain tappable
    // RN supports pointerEvents via style on some platforms; we keep zIndex low and also
    // set an explicit pointerEvents on the element in JSX if needed.
  },
  menuButton: {
    padding: 8,
  },
  keyboardContainer: {
    flex: 1,
  },
  messagesContainer: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  messageContainer: {
    marginVertical: 4,
  },
  messageBubble: {
    maxWidth: '80%',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 14,
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#01AFD1',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  botMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E9F2FB',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  imageMessageContainer: {
    maxWidth: '80%',
    borderRadius: 20,
    overflow: 'hidden',
  },
  userImageContainer: {
    alignSelf: 'flex-end',
  },
  botImageContainer: {
    alignSelf: 'flex-start',
  },
  reactionContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    marginLeft: 8,
  },
  reactionButton: {
    padding: 8,
    marginRight: 8,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
    letterSpacing: 0.1,
  },
  userMessageText: {
    color: '#FFFFFF',
  },
  botMessageText: {
    color: '#043263',
  },
  timestamp: {
    fontSize: 12,
    color: '#6B7A8A',
    marginTop: 6,
  },
  timestampRight: {
    textAlign: 'right',
    alignSelf: 'flex-end',
  },
  timestampLeft: {
    textAlign: 'left',
    alignSelf: 'flex-start',
  },
  messageImage: {
    width: 210,
    height: 210,
    borderRadius: 12,
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#FFFFFF',
    minHeight: 64,
    borderTopWidth: 0,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.03,
    shadowRadius: 6,
    elevation: 4,
  },
  loadingMessage: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  wakeWordIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E5ECFF',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  wakeWordErrorIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEE2E2',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  wakeWordText: {
    color: '#01AFD1',
    fontSize: 11,
    fontWeight: '600',
    marginLeft: 4,
  },
  wakeWordErrorText: {
    color: '#B91C1C',
    fontSize: 11,
    fontWeight: '600',
    marginLeft: 6,
    maxWidth: 150,
  },
  wakeWordTextActive: {
    color: '#10B981',
  },
  pulseIndicator: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#01AFD1',
    marginRight: 6,
  },
  pulseActive: {
    backgroundColor: '#10B981',
  },
});
