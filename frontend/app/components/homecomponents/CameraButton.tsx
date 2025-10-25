import React, { useState } from 'react';
import { TouchableOpacity, StyleSheet, Alert, Modal, View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';

interface CameraButtonProps {
  onImageCaptured: (imageUri: string) => void;
}

export default function CameraButton({ onImageCaptured }: CameraButtonProps) {
  const [showOptions, setShowOptions] = useState(false);

  const handleCameraLaunch = async () => {
    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    
    if (status !== 'granted') {
      console.log('Camera permission denied');
      Alert.alert('Permission Required', 'Camera permission is needed to take photos.');
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
    setShowOptions(false);
  };

  const handleLibraryLaunch = async () => {
    // Request media library permissions
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      console.log('Media library permission denied');
      Alert.alert('Permission Required', 'Photo library permission is needed to select images.');
      return;
    }

    // Launch image library
    const result = await ImagePicker.launchImageLibraryAsync({
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
    setShowOptions(false);
  };

  const showImagePickerOptions = () => {
    Alert.alert(
      'Select Image',
      'Choose how you want to add an image',
      [
        {
          text: 'Camera',
          onPress: handleCameraLaunch,
        },
        {
          text: 'Photo Library',
          onPress: handleLibraryLaunch,
        },
        {
          text: 'Cancel',
          style: 'cancel',
        },
      ]
    );
  };

  return (
    <TouchableOpacity style={styles.cameraButton} onPress={showImagePickerOptions}>
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
