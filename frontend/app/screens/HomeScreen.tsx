import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ScrollView, KeyboardAvoidingView, Platform, StatusBar, ActivityIndicator, Linking } from 'react-native';
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

export default function HomeScreen() {
  const [messages, setMessages] = useState<Array<{id: string, text: string, timestamp: Date, isUser: boolean, imageUri?: string}>>([]);
  const [inputText, setInputText] = useState('');
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<{latitude: number, longitude: number} | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  
  // Auto-camera state
  const [cameraShownForCurrentFocus, setCameraShownForCurrentFocus] = useState(false);
  const [cameraPermissionStatus, setCameraPermissionStatus] = useState<ImagePicker.PermissionStatus | null>(null);

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
        formData.append('user_id', 'demo_user');
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

            // Handle TTS if enabled and audio data is available
            console.log('TTS Debug: ttsEnabled =', ttsEnabled);
            console.log('TTS Debug: result.tts_audio_data exists =', !!result.tts_audio_data);
            console.log('TTS Debug: result.tts_audio_data length =', result.tts_audio_data?.length || 0);
            
            if (ttsEnabled && result.tts_audio_data) {
              try {
                console.log('TTS Debug: Processing audio data...');
                console.log('TTS Debug: Audio data type:', typeof result.tts_audio_data);
                console.log('TTS Debug: Audio data first 100 chars:', result.tts_audio_data.substring(0, 100));
                
                const audioData = result.tts_audio_data;
                
                // Check if FileSystem is available
                console.log('TTS Debug: FileSystem available:', !!FileSystem);
                console.log('TTS Debug: FileSystem.documentDirectory:', FileSystem.documentDirectory);
                console.log('TTS Debug: FileSystem.EncodingType available:', !!FileSystem.EncodingType);
                
                if (!FileSystem || !FileSystem.EncodingType) {
                  console.log('TTS Debug: expo-file-system not available, trying alternative approach...');
                  
                  // Fallback: Try using data URL with expo-av directly
                  const dataUrl = `data:audio/mp3;base64,${audioData}`;
                  console.log('TTS Debug: Using data URL approach');
                  
                  const { sound } = await Audio.Sound.createAsync(
                    { uri: dataUrl },
                    { shouldPlay: true }
                  );
                  
                  console.log('TTS Debug: Audio started playing via data URL');
                  
                  sound.setOnPlaybackStatusUpdate((status) => {
                    console.log('TTS Debug: Playback status update:', status);
                    if (status.isLoaded && status.didJustFinish) {
                      console.log('TTS Debug: Audio finished playing');
                      sound.unloadAsync();
                    }
                  });
                  
                  return; // Exit early since we used the fallback
                }
                
                // Write base64 audio data to a temporary file
                const fileName = `tts_audio_${Date.now()}.mp3`;
                const fileUri = `${FileSystem.documentDirectory}${fileName}`;
                
                console.log('TTS Debug: Writing audio to file:', fileUri);
                console.log('TTS Debug: Audio data length:', audioData.length);
                
                await FileSystem.writeAsStringAsync(fileUri, audioData, {
                  encoding: FileSystem.EncodingType.Base64,
                });
                
                console.log('TTS Debug: Audio file written successfully');
                
                // Check if file exists
                const fileInfo = await FileSystem.getInfoAsync(fileUri);
                console.log('TTS Debug: File exists:', fileInfo.exists);
                console.log('TTS Debug: File size:', fileInfo.size);
                
                // Check if Audio is available
                console.log('TTS Debug: Audio available:', !!Audio);
                console.log('TTS Debug: Audio.Sound available:', !!Audio.Sound);
                
                // Play the audio file using expo-av
                console.log('TTS Debug: Creating audio sound...');
                const { sound } = await Audio.Sound.createAsync(
                  { uri: fileUri },
                  { shouldPlay: true }
                );
                
                console.log('TTS Debug: Audio sound created successfully');
                console.log('TTS Debug: Audio started playing');
                
                // Clean up the file after playback
                sound.setOnPlaybackStatusUpdate((status) => {
                  console.log('TTS Debug: Playback status update:', status);
                  if (status.isLoaded && status.didJustFinish) {
                    console.log('TTS Debug: Audio finished playing');
                    sound.unloadAsync();
                    FileSystem.deleteAsync(fileUri, { idempotent: true });
                  }
                });
                
              } catch (error) {
                console.error('TTS Debug: TTS playback error:', error);
                console.error('TTS Debug: Error stack:', error.stack);
                console.error('TTS Debug: Error message:', error.message);
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
      formData.append('user_id', 'demo_user');
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
              console.log('🔊 Playing TTS for image response...');
              const audioData = result.data.response.tts_audio_data;
              
              if (!FileSystem || !FileSystem.EncodingType) {
                // Fallback: Try using data URL with expo-av directly
                const dataUrl = `data:audio/mp3;base64,${audioData}`;
                
                const { sound } = await Audio.Sound.createAsync(
                  { uri: dataUrl },
                  { shouldPlay: true }
                );
                
                sound.setOnPlaybackStatusUpdate((status) => {
                  if (status.isLoaded && status.didJustFinish) {
                    sound.unloadAsync();
                  }
                });
                
                return;
              }
              
              // Write base64 audio data to a temporary file
              const fileName = `tts_audio_${Date.now()}.mp3`;
              const fileUri = `${FileSystem.documentDirectory}${fileName}`;
              
              await FileSystem.writeAsStringAsync(fileUri, audioData, {
                encoding: FileSystem.EncodingType.Base64,
              });
              
              // Play the audio file using expo-av
              const { sound } = await Audio.Sound.createAsync(
                { uri: fileUri },
                { shouldPlay: true }
              );
              
              // Clean up the file after playback
              sound.setOnPlaybackStatusUpdate((status) => {
                if (status.isLoaded && status.didJustFinish) {
                  sound.unloadAsync();
                  FileSystem.deleteAsync(fileUri, { idempotent: true });
                }
              });
              
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
        formData.append('user_id', 'demo_user');
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
  
            // Handle TTS if enabled and audio data is available
            console.log('TTS Debug: ttsEnabled =', ttsEnabled);
            console.log('TTS Debug: result.tts_audio_data exists =', !!result.tts_audio_data);
            console.log('TTS Debug: result.tts_audio_data length =', result.tts_audio_data?.length || 0);
            
            if (ttsEnabled && result.tts_audio_data) {
              try {
                console.log('TTS Debug: Processing audio data...');
                console.log('TTS Debug: Audio data type:', typeof result.tts_audio_data);
                console.log('TTS Debug: Audio data first 100 chars:', result.tts_audio_data.substring(0, 100));
                
                const audioData = result.tts_audio_data;
                
                // Check if FileSystem is available
                console.log('TTS Debug: FileSystem available:', !!FileSystem);
                console.log('TTS Debug: FileSystem.documentDirectory:', FileSystem.documentDirectory);
                console.log('TTS Debug: FileSystem.EncodingType available:', !!FileSystem.EncodingType);
                
                if (!FileSystem || !FileSystem.EncodingType) {
                  console.log('TTS Debug: expo-file-system not available, trying alternative approach...');
                  
                  // Fallback: Try using data URL with expo-av directly
                  const dataUrl = `data:audio/mp3;base64,${audioData}`;
                  console.log('TTS Debug: Using data URL approach');
                  
                  const { sound } = await Audio.Sound.createAsync(
                    { uri: dataUrl },
                    { shouldPlay: true }
                  );
                  
                  console.log('TTS Debug: Audio started playing via data URL');
                  
                  sound.setOnPlaybackStatusUpdate((status) => {
                    console.log('TTS Debug: Playback status update:', status);
                    if (status.isLoaded && status.didJustFinish) {
                      console.log('TTS Debug: Audio finished playing');
                      sound.unloadAsync();
                    }
                  });
                  
                  return; // Exit early since we used the fallback
                }
                
                // Write base64 audio data to a temporary file
                const fileName = `tts_audio_${Date.now()}.mp3`;
                const fileUri = `${FileSystem.documentDirectory}${fileName}`;
                
                console.log('TTS Debug: Writing audio to file:', fileUri);
                console.log('TTS Debug: Audio data length:', audioData.length);
                
                await FileSystem.writeAsStringAsync(fileUri, audioData, {
                  encoding: FileSystem.EncodingType.Base64,
                });
                
                console.log('TTS Debug: Audio file written successfully');
                
                // Check if file exists
                const fileInfo = await FileSystem.getInfoAsync(fileUri);
                console.log('TTS Debug: File exists:', fileInfo.exists);
                console.log('TTS Debug: File size:', fileInfo.size);
                
                // Check if Audio is available
                console.log('TTS Debug: Audio available:', !!Audio);
                console.log('TTS Debug: Audio.Sound available:', !!Audio.Sound);
                
                // Play the audio file using expo-av
                console.log('TTS Debug: Creating audio sound...');
                const { sound } = await Audio.Sound.createAsync(
                  { uri: fileUri },
                  { shouldPlay: true }
                );
                
                console.log('TTS Debug: Audio sound created successfully');
                console.log('TTS Debug: Audio started playing');
                
                // Clean up the file after playback
                sound.setOnPlaybackStatusUpdate((status) => {
                  console.log('TTS Debug: Playback status update:', status);
                  if (status.isLoaded && status.didJustFinish) {
                    console.log('TTS Debug: Audio finished playing');
                    sound.unloadAsync();
                    FileSystem.deleteAsync(fileUri, { idempotent: true });
                  }
                });
                
              } catch (error) {
                console.error('TTS Debug: TTS playback error:', error);
                console.error('TTS Debug: Error stack:', error.stack);
                console.error('TTS Debug: Error message:', error.message);
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
        formData.append('user_id', 'demo_user');
        formData.append('session_id', 'demo_session');

        const response = await apiClient.post('/api/voice/speak', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        if (response && response.status === 200) {
          const result = response.data;
          if (result.status === 'success' && result.audio_data) {
            // Play the audio
            const audioData = result.audio_data;
            const audioBlob = new Blob([Uint8Array.from(atob(audioData), c => c.charCodeAt(0))], { type: 'audio/mp3' });
            const audioUrl = URL.createObjectURL(audioBlob);
            
            const audio = new Audio(audioUrl);
            audio.play().catch(error => {
              console.error('Error playing TTS audio:', error);
            });
            
            // Clean up the URL after playing
            audio.onended = () => {
              URL.revokeObjectURL(audioUrl);
            };
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
          <TouchableOpacity style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.upgradeButton}>
            <Text style={styles.upgradeText}>Hermes</Text>
          </TouchableOpacity>
          <View style={styles.headerRightContainer}>
            <TouchableOpacity 
              style={[styles.ttsToggle, ttsEnabled && styles.ttsToggleActive]}
              onPress={() => setTtsEnabled(!ttsEnabled)}
            >
              <Ionicons 
                name="volume-high" 
                size={20} 
                color={ttsEnabled ? "#FFFFFF" : "#01AFD1"} 
              />
            </TouchableOpacity>
            <TouchableOpacity 
              style={styles.ttsToggle}
              onPress={handleGenerateJournal}
              accessibilityLabel="Generate journal from latest"
            >
              <Ionicons name="book-outline" size={20} color="#01AFD1" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.menuButton}>
              <Ionicons name="ellipsis-horizontal" size={24} color="#FFFFFF" />
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
                <TouchableOpacity style={styles.reactionButton}>
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
  ttsToggle: {
    padding: 8,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: '#E5ECFF',
  },
  ttsToggleActive: {
    backgroundColor: '#01AFD1',
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
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#01AFD1',
  },
  botMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5ECFF',
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
    lineHeight: 20,
  },
  userMessageText: {
    color: '#FFFFFF',
  },
  botMessageText: {
    color: '#043263',
  },
  timestamp: {
    fontSize: 12,
    color: '#043263',
    marginTop: 4,
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
    width: 200,
    height: 200,
    borderRadius: 15,
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E5ECFF',
    minHeight: 60,
  },
  loadingMessage: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
});
