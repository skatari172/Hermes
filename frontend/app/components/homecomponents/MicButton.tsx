import React, { useState } from 'react';
import { TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';

interface MicButtonProps {
  onAudioRecorded: (audioUri: string) => void;
}

export default function MicButton({ onAudioRecorded }: MicButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);

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

      // Start recording
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
      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });
      
      const uri = recording.getURI();
      console.log('Recording stopped and stored at', uri);
      
      if (uri) {
        onAudioRecorded(uri);
      }
      
      setRecording(null);
    } catch (err) {
      console.error('Failed to stop recording', err);
    }
  };

  const handleMicPress = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <TouchableOpacity 
      style={[styles.micButton, isRecording && styles.micButtonRecording]} 
      onPress={handleMicPress}
    >
      <Ionicons 
        name={isRecording ? "stop" : "mic-outline"} 
        size={20} 
        color={isRecording ? "#FFFFFF" : "#043263"} 
      />
    </TouchableOpacity>
  );
}

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
});
