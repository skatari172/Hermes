import { Linking, Alert } from 'react-native';
import type { LocationObjectCoords } from 'expo-location';

// Calculate distance between two coordinates in meters
export const distanceMeters = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = lat1 * Math.PI / 180;
  const φ2 = lat2 * Math.PI / 180;
  const Δφ = (lat2 - lat1) * Math.PI / 180;
  const Δλ = (lon2 - lon1) * Math.PI / 180;

  const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) *
    Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
};

// Format distance for display
export const formatDistance = (meters: number): string => {
  if (meters < 1000) {
    return `${Math.round(meters)}m`;
  } else {
    return `${(meters / 1000).toFixed(1)}km`;
  }
};

// Calculate distance and return formatted string
export const calculateDistance = (
  userLocation: LocationObjectCoords | null,
  pinLatitude: number,
  pinLongitude: number
): string | null => {
  if (!userLocation) return null;
  
  const meters = distanceMeters(
    userLocation.latitude,
    userLocation.longitude,
    pinLatitude,
    pinLongitude
  );
  
  return formatDistance(meters);
};

// Handle navigation to pin
export const handleNavigateToPin = async (
  userLocation: LocationObjectCoords | null,
  pinLatitude: number,
  pinLongitude: number
): Promise<boolean> => {
  try {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${pinLatitude},${pinLongitude}`;
    const supported = await Linking.canOpenURL(url);
    
    if (supported) {
      await Linking.openURL(url);
      return true;
    } else {
      Alert.alert('Error', 'Unable to open maps application');
      return false;
    }
  } catch (error) {
    Alert.alert('Error', 'Unable to open directions');
    return false;
  }
};

// Get category icon and colors
export const getCategoryIcon = (category: string) => {
  const icons = {
    food: { name: 'food', bg: '#FF6B6B', color: '#FFFFFF' },
    drink: { name: 'cup', bg: '#4ECDC4', color: '#FFFFFF' },
    item: { name: 'package-variant', bg: '#45B7D1', color: '#FFFFFF' },
    other: { name: 'help-circle', bg: '#96CEB4', color: '#FFFFFF' },
  };
  
  return icons[category as keyof typeof icons] || icons.other;
};

// Get category colors for UI elements
export const getCategoryColors = (category: string) => {
  const colors = {
    food: { 
      bgColor: '#FFF5F5', 
      borderColor: '#FF6B6B', 
      textColor: '#2D3748' 
    },
    drink: { 
      bgColor: '#F0FDFC', 
      borderColor: '#4ECDC4', 
      textColor: '#2D3748' 
    },
    item: { 
      bgColor: '#EBF8FF', 
      borderColor: '#45B7D1', 
      textColor: '#2D3748' 
    },
    other: { 
      bgColor: '#F0FFF4', 
      borderColor: '#96CEB4', 
      textColor: '#2D3748' 
    },
  };
  
  return colors[category as keyof typeof colors] || colors.other;
};

// Format relative time
export const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) {
    return 'Just now';
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  } else if (diffInSeconds < 604800) {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days} day${days > 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleDateString();
  }
};
