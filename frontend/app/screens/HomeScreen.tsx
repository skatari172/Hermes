import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ScrollView, KeyboardAvoidingView, Platform, StatusBar } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CameraButton, MicButton, TextInput } from '../components/homecomponents';
import * as FileSystem from 'expo-file-system';
import { Audio } from 'expo-av';

export default function HomeScreen() {
  const [messages, setMessages] = useState<Array<{id: string, text: string, timestamp: Date, isUser: boolean, imageUri?: string}>>([]);
  const [inputText, setInputText] = useState('');
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages]);


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

      try {
        // Auto-detect backend URL
        const possibleURLs = [
          'http://10.127.217.215:8000',
          'http://localhost:8000',
          'http://127.0.0.1:8000',
          'http://10.0.2.2:8000',
          'http://192.168.1.100:8000',
          'http://192.168.0.100:8000',
          'http://192.168.1.101:8000',
          'http://192.168.0.101:8000',
        ];

        let backendURL = 'http://localhost:8000';
        for (const url of possibleURLs) {
          try {
            const healthCheck = await fetch(`${url}/health`);
            if (healthCheck.ok) {
              backendURL = url;
              break;
            }
          } catch (error) {
            // Continue to next URL
          }
        }

        // Send message to backend
        const formData = new FormData();
        formData.append('message', messageText);
        formData.append('user_id', 'demo_user');
        formData.append('session_id', 'demo_session');

        const response = await fetch(`${backendURL}/api/chat`, {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
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
      }
    }
  };

  const handleImageCaptured = (imageUri: string) => {
    const newMessage = {
      id: Date.now().toString(),
      text: '',
      timestamp: new Date(),
      isUser: true,
      imageUri: imageUri
    };
    setMessages(prev => [...prev, newMessage]);
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

  const handleTranscriptionComplete = (transcribedText: string) => {
    // Put the transcribed text into the text input
    setInputText(transcribedText);
  };

  const handleTtsForMessage = async (messageText: string) => {
    if (ttsEnabled && messageText) {
      try {
        // Auto-detect backend URL (same logic as MicButton)
        const possibleURLs = [
          'http://10.127.217.215:8000',
          'http://localhost:8000',
          'http://127.0.0.1:8000',
          'http://10.0.2.2:8000',
          'http://192.168.1.100:8000',
          'http://192.168.0.100:8000',
          'http://192.168.1.101:8000',
          'http://192.168.0.101:8000',
        ];

        let backendURL = 'http://localhost:8000';
        for (const url of possibleURLs) {
          try {
            const healthCheck = await fetch(`${url}/health`);
            if (healthCheck.ok) {
              backendURL = url;
              break;
            }
          } catch (error) {
            // Continue to next URL
          }
        }

        // Call TTS endpoint
        const formData = new FormData();
        formData.append('text', messageText);
        formData.append('user_id', 'demo_user');
        formData.append('session_id', 'demo_session');

        const response = await fetch(`${backendURL}/api/voice/speak`, {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
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
});