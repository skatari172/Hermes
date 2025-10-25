import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from '../../../contexts/AuthContext';
import { userAPI } from '../../../api/apiClient';
import { auth } from '../../../config/firebase';

export default function UserProfileSection() {
  const { user, loading, refreshUser } = useAuth();
  const [profileImage, setProfileImage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [displayNameState, setDisplayNameState] = useState<string | null>(null);
  const [emailState, setEmailState] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setProfileImage(user.photoURL || null);
      setDisplayNameState(user.displayName || null);
      setEmailState(user.email || null);

      // fetch authoritative profile from backend (auth/Firestore)
      (async () => {
        try {
          const current = auth.currentUser;
          if (!current) return;
          const token = await current.getIdToken();
          const resp = await userAPI.getProfile(token);
          console.log('DEBUG: getProfile response', resp);
          const data = resp.data || resp;
          const profile = data.profile || {};
          if (profile.photo_url) {
            console.log('DEBUG: backend profile.photo_url', profile.photo_url);
            setProfileImage(profile.photo_url);
          }
          if (profile.display_name) {
            console.log('DEBUG: backend profile.display_name', profile.display_name);
            setDisplayNameState(profile.display_name);
          }
          if (profile.email) {
            console.log('DEBUG: backend profile.email', profile.email);
            setEmailState(profile.email);
          }
        } catch (e) {
          // silently ignore
        }
      })();
    }
  }, [user]);

  const handleEditProfileImage = async () => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Sorry, we need camera roll permissions to select a photo!', [{ text: 'OK' }]);
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.8,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const selectedUri = result.assets[0].uri;
        if (!user) {
          Alert.alert('Not signed in', 'Please sign in to update your profile picture.');
          return;
        }

        setSaving(true);
        try {
          const formData = new FormData();
          // React Native FormData expects an object with uri, name and type
          const asset = result.assets[0];
          const name = asset.fileName || `profile_${user.uid}.jpg`;
          const type = asset.type || asset.mimeType || 'image/jpeg';

          formData.append('file', {
            uri: selectedUri,
            name,
            type,
          } as any);

          const resp = await userAPI.uploadProfilePhoto(formData);
          console.log('DEBUG: uploadProfilePhoto resp', resp);
          const data = resp.data || resp;
          const photoUrl = data.photo_url || data.photoUrl || data.photoURL || data.photo_url;

          if (photoUrl) {
            console.log('DEBUG: received photoUrl', photoUrl);
            // Update local state immediately
            setProfileImage(photoUrl);

            // Refresh global auth user so other screens see the new photoURL
            try {
              if (typeof refreshUser === 'function') await refreshUser();
            } catch (e) {
              console.warn('Failed to refresh auth user:', e);
            }

            // Also re-fetch backend profile to ensure Firestore/stored url is used
            try {
              const current = auth.currentUser;
              if (current) {
                const token = await current.getIdToken();
                const resp = await userAPI.getProfile(token);
                console.log('DEBUG: post-upload getProfile resp', resp);
                const data = resp.data || resp;
                const profile = data.profile || {};
                if (profile.photo_url) setProfileImage(profile.photo_url);
                if (profile.display_name) setDisplayNameState(profile.display_name);
                if (profile.email) setEmailState(profile.email);
              }
            } catch (e) {
              // ignore
            }
          } else {
            Alert.alert('Upload failed', 'Server did not return a photo URL');
          }
        } catch (err) {
          console.error('Upload failed', err);
          Alert.alert('Upload failed', 'Could not upload image. Please try again.');
        } finally {
          setSaving(false);
        }
      }
    } catch (error) {
      console.error('Error selecting image:', error);
      Alert.alert('Error', 'Failed to select image. Please try again.');
    }
  };

  const displayName = displayNameState ?? user?.displayName ?? 'User';
  const email = emailState ?? user?.email ?? '';

  if (loading) {
    return (
      <View style={styles.profileSection}>
        <ActivityIndicator size="large" color="#01AFD1" />
      </View>
    );
  }

  return (
    <View style={styles.profileSection}>
      <View style={styles.profileImageContainer}>
        <Image 
          source={{ uri: profileImage || 'https://via.placeholder.com/100x100/E5ECFF/043263?text=?' }}
          style={styles.profileImage}
          onError={(e) => console.warn('Image load error', e.nativeEvent || e)}
          onLoad={() => console.log('Image loaded successfully')}
        />
        <TouchableOpacity style={styles.editButton} onPress={handleEditProfileImage}>
          {saving ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <Ionicons name="pencil" size={16} color="#FFFFFF" />
          )}
        </TouchableOpacity>
      </View>
      <Text style={styles.userName}>{displayName}</Text>
      <Text style={styles.userEmail}>{email}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  profileSection: {
    alignItems: 'center',
    paddingVertical: 30,
  },
  profileImageContainer: {
    position: 'relative',
    marginBottom: 16,
  },
  profileImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#E5ECFF',
  },
  editButton: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#01AFD1',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#043263',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 16,
    color: '#666666',
    marginBottom: 16,
  },
});
