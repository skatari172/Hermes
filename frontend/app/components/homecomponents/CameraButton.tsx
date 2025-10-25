import React from 'react';
import { TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';

interface CameraButtonProps {
  onImageCaptured: (imageUri: string) => void;
}

export default function CameraButton({ onImageCaptured }: CameraButtonProps) {
  const handleCameraLaunch = async () => {
    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    
    if (status !== 'granted') {
      console.log('Camera permission denied');
      return;
    }

    // Launch camera
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 1,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      const source = result.assets[0].uri;
      console.log('Image URI: ', source);
      onImageCaptured(source);
    }
  };

  return (
    <TouchableOpacity style={styles.cameraButton} onPress={handleCameraLaunch}>
      <Ionicons name="camera" size={24} color="#043263" />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  cameraButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#E5ECFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
});
