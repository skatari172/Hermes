import React, { useState, forwardRef, useImperativeHandle } from 'react';
import { TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import apiClient from '../../../api/apiClient';
// import { voiceAPI } from '../../../api/apiClient'; // Not used in this component

interface MicButtonProps {
  onAudioRecorded: (audioUri: string) => void;
  onTranscriptionComplete: (text: string) => void;
}

export interface MicButtonRef {
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
}

const MicButton = forwardRef<MicButtonRef, MicButtonProps>(
  ({ onAudioRecorded, onTranscriptionComplete }, ref) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    startRecording,
    stopRecording,
  }));

  const transcribeAudio = async (audioUri: string) => {
    try {
      // Use centralized apiClient which resolves baseURL dynamically

      // Create a FormData object to send the audio file
      const formData = new FormData();
      
      // For React Native, we can directly append the URI as a file
      // Handle different audio formats (.m4a, .caf, .wav)
      const fileExtension = audioUri.split('.').pop()?.toLowerCase();
      let mimeType = 'audio/wav';
      let fileName = 'recording.wav';
      
      if (fileExtension === 'm4a') {
        mimeType = 'audio/mp4';
        fileName = 'recording.m4a';
      } else if (fileExtension === 'caf') {
        mimeType = 'audio/x-caf';
        fileName = 'recording.caf';
      }
      
      formData.append('audio_file', {
        uri: audioUri,
        type: mimeType,
        name: fileName,
      } as any);
      formData.append('session_id', 'demo_session');

      // Send to backend transcription endpoint via apiClient
      const response = await apiClient.post('/api/voice/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return response.data;
    } catch (error) {
      console.error('Error transcribing audio:', error);
      throw error;
    }
  };

  const startRecording = async () => {
    try {
      // Request audio permissions
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        console.log('Microphone permission denied');
        return;
      }

      // Configure audio mode
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      // Start recording with simple WAV format for maximum compatibility
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(recording);
      setIsRecording(true);
      console.log('Recording started');
    } catch (err) {
      console.error('Failed to start recording', err);
    }
  };

  const stopRecording = async () => {
    if (!recording) return;

    try {
      setIsRecording(false);
      setIsProcessing(true);
      
      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });
      
      const uri = recording.getURI();
      console.log('Recording stopped and stored at', uri);
      
      if (uri) {
        onAudioRecorded(uri);
        
        // Send audio to backend for transcription
        try {
          const transcriptionResult = await transcribeAudio(uri);
          onTranscriptionComplete(transcriptionResult.transcribed_text);
        } catch (error) {
          console.error('Transcription failed:', error);
          // Fallback to mock transcription if backend fails
          const mockTranscription = "Transcription failed. Please try again or type your message.";
          onTranscriptionComplete(mockTranscription);
        } finally {
          setIsProcessing(false);
        }
      }
      
      setRecording(null);
    } catch (err) {
      console.error('Failed to stop recording', err);
      setIsProcessing(false);
    }
  };

  const handleMicPress = () => {
    if (isRecording || isProcessing) {
      if (isRecording) {
        stopRecording();
      }
      return;
    }
    startRecording();
  };

  return (
    <TouchableOpacity 
      style={[
        styles.micButton, 
        isRecording && styles.micButtonRecording,
        isProcessing && styles.micButtonProcessing
      ]} 
      onPress={handleMicPress}
      disabled={isProcessing}
    >
      <Ionicons 
        name={
          isProcessing ? "hourglass-outline" : 
          isRecording ? "stop" : "mic-outline"
        } 
        size={20} 
        color={
          isProcessing ? "#043263" :
          isRecording ? "#FFFFFF" : "#043263"
        } 
      />
    </TouchableOpacity>
  );
});

export default MicButton;

const styles = StyleSheet.create({
  micButton: {
    padding: 4,
    marginLeft: 8,
  },
  micButtonRecording: {
    backgroundColor: '#FF4444',
    borderRadius: 20,
    padding: 8,
  },
  micButtonProcessing: {
    backgroundColor: '#FFA500',
    borderRadius: 20,
    padding: 8,
  },
});
