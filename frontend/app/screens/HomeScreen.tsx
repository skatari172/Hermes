import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ScrollView, KeyboardAvoidingView, Platform, StatusBar } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CameraButton, MicButton, TextInput } from '../components/homecomponents';

export default function HomeScreen() {
  const [messages, setMessages] = useState<Array<{id: string, text: string, timestamp: Date, isUser: boolean, imageUri?: string}>>([]);
  const [inputText, setInputText] = useState('');
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

  const handleSubmitMessage = () => {
    if (inputText.trim()) {
      const newMessage = {
        id: Date.now().toString(),
        text: inputText.trim(),
        timestamp: new Date(),
        isUser: true
      };
      setMessages(prev => [...prev, newMessage]);
      setInputText('');
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
          <TouchableOpacity style={styles.menuButton}>
            <Ionicons name="ellipsis-horizontal" size={24} color="#FFFFFF" />
          </TouchableOpacity>
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