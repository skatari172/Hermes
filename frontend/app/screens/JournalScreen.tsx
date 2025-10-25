import React, { useEffect, useState, useRef, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Modal, TextInput, TouchableOpacity, Alert, ScrollView, FlatList, Image, PanResponder, Animated, Platform, RefreshControl, Keyboard } from 'react-native';
import type { LocationObjectCoords } from 'expo-location';
import MapView, { Marker } from 'react-native-maps';
import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { calculateDistance, handleNavigateToPin, getCategoryIcon, formatRelativeTime, distanceMeters, formatDistance, getCategoryColors } from '../../utils/helpers';
import { journalStyles } from '../../styles/journalStyles';
import { pinsStyles } from '../../styles/pinsStyles';
import { useNavigation } from '@react-navigation/native';
import { usePins } from '../../contexts/usePins';
import apiClient from '../../api/apiClient';

// Define Pin type locally since we're not importing from apiService
interface Pin {
  id: string;
  category: string;
  description?: string;
  title?: string;
  latitude: number;
  longitude: number;
  createdAt?: string;
  upVotes?: number;
  downVotes?: number;
}

export default function JournalScreen() {
  const [location, setLocation] = useState<LocationObjectCoords | null>(null);
  const [loading, setLoading] = useState(true);
  
  // View mode state for toggle between map and list
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  
  // Pins list states (when in list view)
  const [refreshing, setRefreshing] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [maxDistance, setMaxDistance] = useState<number>(10); // in miles
  const [sortOption, setSortOption] = useState<'none' | 'distance' | 'time'>('none');
  
  // Use the pins hook to manage pin data from API
  const { pins: droppedPins, loading: pinsLoading, refreshPins, addPin, updatePinVotes } = usePins();
  
  const [mapRef, setMapRef] = useState<MapView | null>(null);
  
  // Modal states
  const [showPinModal, setShowPinModal] = useState(false);
  const [tempPinLocation, setTempPinLocation] = useState<{latitude: number, longitude: number} | null>(null);
  const [pinCategory, setPinCategory] = useState('food');
  const [pinDescription, setPinDescription] = useState('');
  const [pinTitle, setPinTitle] = useState('');
  const [pinPhoto, setPinPhoto] = useState<string | null>(null);
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false);
  
  // Refs for keyboard handling
  const scrollViewRef = useRef<ScrollView>(null);
  const titleInputRef = useRef<TextInput>(null);
  const descriptionInputRef = useRef<TextInput>(null);
  
  // Navigation for refresh functionality
  const navigation = useNavigation();
  
  // Pin detail modal states (local state for normal pin details)
  const [showPinDetailModal, setShowPinDetailModal] = useState(false);
    const [localSelectedPin, setLocalSelectedPin] = useState<Pin | null>(null);

  // Swipe gesture states
  const [modalTranslateY] = useState(new Animated.Value(0));
  const [modalOpacity] = useState(new Animated.Value(1));

  const categories = [
    { label: 'Food', value: 'food' },
    { label: 'Drink', value: 'drink' },
    { label: 'Item', value: 'item' },
    { label: 'Other', value: 'other' },
  ];

  // Pan responder for swipe-to-dismiss functionality
  const panResponder = PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: (evt, gestureState) => {
      // Only respond to vertical swipes downward from the header
      return Math.abs(gestureState.dy) > Math.abs(gestureState.dx) && gestureState.dy > 10;
    },
    onPanResponderGrant: () => {
      // No offset needed, start fresh
    },
    onPanResponderMove: (evt, gestureState) => {
      // Only allow downward movement
      if (gestureState.dy >= 0) {
        modalTranslateY.setValue(gestureState.dy);
        // Fade out as user swipes down
        const opacity = Math.max(0.3, 1 - (gestureState.dy / 300));
        modalOpacity.setValue(opacity);
      }
    },
    onPanResponderRelease: (evt, gestureState) => {
      // Require a much higher threshold - need to swipe down at least 250 pixels or very fast velocity
      if (gestureState.dy > 250 || gestureState.vy > 1.5) {
        // Animate out and close modal
        Animated.parallel([
          Animated.timing(modalTranslateY, {
            toValue: 500,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(modalOpacity, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
        ]).start(() => {
          // Close modal and reset animations
          handleClosePinDetail();
          
          // Reset animation values
          modalTranslateY.setValue(0);
          modalOpacity.setValue(1);
        });
      } else {
        // Snap back to original position with stronger spring
        Animated.parallel([
          Animated.spring(modalTranslateY, {
            toValue: 0,
            useNativeDriver: true,
            tension: 120,
            friction: 10,
          }),
          Animated.timing(modalOpacity, {
            toValue: 1,
            duration: 250,
            useNativeDriver: true,
          }),
        ]).start();
      }
    },
  });

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setLoading(false);
        return;
      }
      let loc = await Location.getCurrentPositionAsync({});
      setLocation(loc.coords);
      setLoading(false);
    })();

    // Pins are loaded automatically by the usePins hook
  }, []);

  // Simple refresh on navigation focus (when tab is pressed while already focused)
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      // Only refresh if we already have pins (avoid refreshing on initial load)
      if (droppedPins.length > 0) {
        refreshPins();
      }
    });
    return unsubscribe;
  }, [navigation, droppedPins.length, mapRef, refreshPins]);

  // Keyboard event listeners for smooth scrolling
  useEffect(() => {
    const keyboardWillShow = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow',
      (event) => {
        // Scroll to show the entire description box above the keyboard
        if (scrollViewRef.current) {
          // Scroll to the bottom to ensure description box is fully visible
          scrollViewRef.current.scrollToEnd({ animated: true });
        }
      }
    );

    return () => {
      keyboardWillShow.remove();
    };
  }, [pinPhoto]);

  const handleLongPress = (event: any) => {
    const { latitude, longitude } = event.nativeEvent.coordinate;
    setTempPinLocation({ latitude, longitude });
    setShowPinModal(true);
    setPinCategory('food');
    setPinDescription('');
    setPinTitle('');
    setPinPhoto(null);
  };

  const handleTakePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Camera permission is required to take photos');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
    });

    if (!result.canceled && result.assets[0]) {
      setPinPhoto(result.assets[0].uri);
    }
  };

  const handleAddPin = async () => {
    if (!tempPinLocation) return;
    
    // Check if image is required
    if (!pinPhoto) {
      Alert.alert('Image Required', 'Please take a photo before creating a pin.');
      return;
    }
    
    try {
      // Use the API client to create the pin
      const pinData = {
        category: pinCategory,
        description: pinDescription,
        title: pinTitle,
        longitude: tempPinLocation.longitude,
        latitude: tempPinLocation.latitude,
        imageFile: pinPhoto ? {
          uri: pinPhoto,
          type: 'image/jpeg',
          name: `pin-image-${Date.now()}.jpg`,
        } as any : undefined,
      };

      const response = await apiClient.post('/pins', pinData);
      const createdPin = response.data;
      
      // Add pin using the hook
      addPin(createdPin);
      setShowPinModal(false);
      setTempPinLocation(null);
      Alert.alert('Success', 'Pin added successfully!');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to add pin';
      Alert.alert('Error', errorMessage);
      console.error('Error adding pin:', error);
    }
  };

  const handleCancelPin = () => {
    setShowPinModal(false);
    setTempPinLocation(null);
    setPinCategory('food');
    setPinDescription('');
    setPinTitle('');
    setPinPhoto(null);
  };

  const handleMarkerPress = (pin: any) => {
    setLocalSelectedPin(pin);
    setShowPinDetailModal(true);
    
    // Zoom to the selected pin using camera
    if (mapRef) {
      const camera = {
        center: {
          latitude: pin.latitude - 1.3e-3,
          longitude: pin.longitude,
        },
        zoom: 18, // Same zoom level as pins tab
        heading: 0,
        pitch: 0,
      };
      
      console.log('Zooming to pin from map marker:', camera);
      mapRef.animateCamera(camera, { duration: 1000 });
    }
  };

  const handleClosePinDetail = () => {
    setShowPinDetailModal(false);
    setLocalSelectedPin(null);
  };

  // Pins list helper functions
  const availableCategories = ['food', 'drink', 'item'];
  
  const toggleCategory = (category: string) => {
    setSelectedCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    refreshPins();
    setRefreshing(false);
  }, [refreshPins]);

  const getFilteredPins = useCallback(() => {
    let filtered = [...droppedPins];
    
    // Filter by categories
    if (selectedCategories.length > 0) {
      filtered = filtered.filter(pin => selectedCategories.includes(pin.category));
    }
    
    // Filter by distance if user location is available
    if (location) {
      filtered = filtered.filter(pin => {
        const meters = distanceMeters(location.latitude, location.longitude, pin.latitude, pin.longitude);
        const miles = meters * 0.000621371;
        return miles <= maxDistance;
      });
      
      // Sort based on selected option
      if (sortOption === 'distance') {
        filtered.sort((a, b) => {
          const distanceA = distanceMeters(location.latitude, location.longitude, a.latitude, a.longitude);
          const distanceB = distanceMeters(location.latitude, location.longitude, b.latitude, b.longitude);
          return distanceA - distanceB;
        });
      } else if (sortOption === 'time') {
        filtered.sort((a, b) => {
          const timeA = new Date(a.createdAt || 0).getTime();
          const timeB = new Date(b.createdAt || 0).getTime();
          return timeB - timeA; // Most recent first
        });
      }
    } else if (sortOption === 'time') {
      // Can sort by time even without location
      filtered.sort((a, b) => {
        const timeA = new Date(a.createdAt || 0).getTime();
        const timeB = new Date(b.createdAt || 0).getTime();
        return timeB - timeA; // Most recent first
      });
    }
    
    return filtered;
  }, [droppedPins, selectedCategories, maxDistance, location, sortOption]);

  const handlePinPress = (pin: Pin) => {
    setLocalSelectedPin(pin);
    setShowPinDetailModal(true);
  };

  const renderPinItem = ({ item }: { item: Pin }) => {
    let distance: string | null = null;
    if (location) {
      const meters = distanceMeters(location.latitude, location.longitude, item.latitude, item.longitude);
      distance = formatDistance(meters);
    }
    const { bgColor, borderColor, textColor } = getCategoryColors(item.category);
    const icon = getCategoryIcon(item.category);
    
    return (
      <TouchableOpacity 
        style={[pinsStyles.itemContainer, { backgroundColor: bgColor }]}
        onPress={() => handlePinPress(item)}
        activeOpacity={0.7}
      >
        {/* Pin Header with Circular Icon and Title */}
        <View style={pinsStyles.pinHeaderContainer}>
          {/* Circular Category Icon */}
          <View style={[pinsStyles.categoryCircle, { backgroundColor: icon.bg }]}>
            <MaterialCommunityIcons 
              name={icon.name as any} 
              size={28} 
              color={icon.color} 
            />
          </View>
          
          {/* Title and Info */}
          <View style={pinsStyles.pinInfoContainer}>
            <Text style={[pinsStyles.title, { color: textColor }]}>
              {item.title || 'Untitled'}
            </Text>
            <View style={pinsStyles.pinMetaInfo}>
              {distance && (
                <Text style={[pinsStyles.distance, { color: borderColor, fontSize: 13, fontWeight: '600' }]}>
                  {distance}
                </Text>
              )}
              {item.createdAt && (
                <Text style={pinsStyles.timestamp}>{formatRelativeTime(item.createdAt)}</Text>
              )}
            </View>
          </View>
        </View>
        
        <Text style={[pinsStyles.description, { color: textColor }]}>{item.description || 'No description'}</Text>
        
        {/* Creator Info - Bottom Right */}
        <View style={pinsStyles.creatorInfoContainer}>
          <Text style={pinsStyles.tapHint}>Tap to view details</Text>
          {(item as any).createdByUsername && (
            <View style={pinsStyles.creatorBadge}>
              {(item as any).createdByProfileImage ? (
                <Image 
                  source={{ uri: (item as any).createdByProfileImage }} 
                  style={pinsStyles.creatorAvatar}
                />
              ) : (
                <View style={pinsStyles.creatorAvatarPlaceholder}>
                  <MaterialCommunityIcons name="account" size={16} color="#8E8E93" />
                </View>
              )}
              <Text style={pinsStyles.creatorText}>by {(item as any).createdByUsername}</Text>
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={{ flex: 1, paddingBottom: 120 }}>
      {/* View Toggle Buttons */}
      <View style={journalStyles.toggleContainer}>
        <TouchableOpacity
          style={[
            journalStyles.toggleButton,
            viewMode === 'map' && journalStyles.toggleButtonActive
          ]}
          onPress={() => setViewMode('map')}
        >
          <MaterialCommunityIcons 
            name="map" 
            size={20} 
            color={viewMode === 'map' ? '#FFFFFF' : '#007AFF'} 
          />
          <Text style={[
            journalStyles.toggleButtonText,
            viewMode === 'map' && journalStyles.toggleButtonTextActive
          ]}>
            Map
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[
            journalStyles.toggleButton,
            viewMode === 'list' && journalStyles.toggleButtonActive
          ]}
          onPress={() => setViewMode('list')}
        >
          <MaterialCommunityIcons 
            name="format-list-bulleted" 
            size={20} 
            color={viewMode === 'list' ? '#FFFFFF' : '#007AFF'} 
          />
          <Text style={[
            journalStyles.toggleButtonText,
            viewMode === 'list' && journalStyles.toggleButtonTextActive
          ]}>
            List
          </Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator size="large" style={{ flex: 1 }} />
      ) : (
        <>
          {viewMode === 'map' ? (
            <MapView
              ref={setMapRef}
              style={StyleSheet.absoluteFill}
              showsUserLocation={true}
              onLongPress={handleLongPress}
              zoomEnabled={true}
              scrollEnabled={true}
              pitchEnabled={true}
              rotateEnabled={false}
              onMapReady={() => {
                console.log('�️ Map is ready');
              }}
        >
          {droppedPins.map((pin) => {
            const icon = getCategoryIcon(pin.category);
            
            return (
              <Marker
                key={pin.id}
                coordinate={{ latitude: pin.latitude, longitude: pin.longitude }}
                onPress={() => handleMarkerPress(pin)}
              >
                <View style={journalStyles.markerWrapper}>
                  <View style={[journalStyles.markerBubble, { backgroundColor: icon.bg }]}> 
                    <MaterialCommunityIcons name={icon.name as any} size={18} color={icon.color} />
                  </View>
                  <View style={[journalStyles.markerPointer, { borderTopColor: icon.bg }]} />
                </View>
              </Marker>
            );
          })}
        </MapView>
          ) : (
            // List View
            <View style={{ flex: 1 }}>
              {/* Filter Header */}
              <View style={journalStyles.filterHeader}>
                <View style={journalStyles.filterRow}>
                  <View style={journalStyles.categoryChipsContainer}>
                    {availableCategories.map((category) => (
                      <TouchableOpacity
                        key={category}
                        style={[
                          journalStyles.categoryChip,
                          selectedCategories.includes(category) && journalStyles.categoryChipSelected
                        ]}
                        onPress={() => toggleCategory(category)}
                      >
                        <Text style={[
                          journalStyles.categoryChipText,
                          selectedCategories.includes(category) && journalStyles.categoryChipTextSelected
                        ]}>
                          {category}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  
                  <TouchableOpacity 
                    style={[
                      journalStyles.sortButton,
                      sortOption !== 'none' && journalStyles.sortButtonActive
                    ]}
                    onPress={() => {
                      const options = ['none', 'distance', 'time'] as const;
                      const currentIndex = options.indexOf(sortOption);
                      const nextIndex = (currentIndex + 1) % options.length;
                      setSortOption(options[nextIndex]);
                    }}
                  >
                    <Text style={[
                      journalStyles.sortButtonText,
                      sortOption !== 'none' && journalStyles.sortButtonTextActive
                    ]}>
                      Sort: {sortOption === 'none' ? 'None' : sortOption === 'distance' ? 'Distance' : 'Recent'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* Pins List */}
              <FlatList
                data={getFilteredPins()}
                renderItem={renderPinItem}
                keyExtractor={(item) => item.id}
                refreshControl={
                  <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
                }
                showsVerticalScrollIndicator={false}
                contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
                ListEmptyComponent={
                  <View style={journalStyles.emptyContainer}>
                    <MaterialCommunityIcons name="map-marker-off" size={48} color="#8E8E93" />
                    <Text style={journalStyles.emptyText}>No pins found</Text>
                    <Text style={journalStyles.emptySubtext}>
                      {selectedCategories.length > 0 || sortOption !== 'none' 
                        ? 'Try adjusting your filters' 
                        : 'Add a pin by long pressing on the map'
                      }
                    </Text>
                  </View>
                }
              />
            </View>
          )}
        </>
      )}
      
      {/* Pin Details Modal */}
      <Modal
        visible={showPinModal}
        animationType="slide"
        transparent={false}
        onRequestClose={handleCancelPin}
      >
        <View style={{ flex: 1, backgroundColor: 'white' }}>
          <View style={journalStyles.modalContent}>
            {/* Scrollable Content */}
            <ScrollView 
              ref={scrollViewRef}
              showsVerticalScrollIndicator={false}
              keyboardShouldPersistTaps="handled"
              style={{ flex: 1 }}
              contentContainerStyle={{ paddingBottom: 200 }}
              nestedScrollEnabled={true}
            >
              <Text style={journalStyles.modalTitle}>Add Pin Details</Text>
              
              {/* Category Picker */}
              <Text style={journalStyles.label}>Category</Text>
              <TouchableOpacity
                style={journalStyles.categoryButton}
                onPress={() => setShowCategoryDropdown(!showCategoryDropdown)}
              >
                <Text style={journalStyles.categoryButtonText}>
                  {categories.find(cat => cat.value === pinCategory)?.label || '🍕 Food'}
                </Text>
                <Text style={journalStyles.dropdownArrow}>{showCategoryDropdown ? '▲' : '▼'}</Text>
              </TouchableOpacity>
              
              {showCategoryDropdown && (
                <View style={journalStyles.categoryDropdown}>
                  <ScrollView 
                    style={journalStyles.categoryScrollView}
                    nestedScrollEnabled={true}
                    showsVerticalScrollIndicator={true}
                  >
                    {categories.map((category) => (
                      <TouchableOpacity
                        key={category.value}
                        style={[
                          journalStyles.categoryOption,
                          pinCategory === category.value && journalStyles.selectedCategoryOption
                        ]}
                        onPress={() => {
                          setPinCategory(category.value);
                          setShowCategoryDropdown(false);
                        }}
                      >
                        <Text style={[
                          journalStyles.categoryOptionText,
                          pinCategory === category.value && journalStyles.selectedCategoryOptionText
                        ]}>
                          {category.label}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>
                </View>
              )}

              {/* Title Input */}
              <Text style={journalStyles.label}>Title</Text>
              <TextInput
                ref={titleInputRef}
                style={journalStyles.titleInput}
                placeholder="Enter a title for this pin..."
                value={pinTitle}
                onChangeText={setPinTitle}
                maxLength={50}
              />

              {/* Photo Button */}
              <Text style={journalStyles.label}>Photo *</Text>
              <TouchableOpacity
                style={journalStyles.photoButton}
                onPress={handleTakePhoto}
              >
                <Text style={journalStyles.photoButtonText}>
                  {pinPhoto ? 'Photo Added ✓' : 'Take Photo (Required)'}
                </Text>
              </TouchableOpacity>

              {/* Photo Preview */}
              {pinPhoto && (
                <View style={journalStyles.photoPreviewContainer}>
                  <Image 
                    source={{ uri: pinPhoto }} 
                    style={journalStyles.photoPreview} 
                    resizeMode="cover"
                  />
                  <TouchableOpacity 
                    style={journalStyles.removePhotoButton}
                    onPress={() => setPinPhoto(null)}
                  >
                    <MaterialCommunityIcons name="close-circle" size={24} color="#ff4444" />
                  </TouchableOpacity>
                </View>
              )}

              {/* Description Input */}
              <Text style={journalStyles.label}>Description</Text>
              <TextInput
                ref={descriptionInputRef}
                style={journalStyles.descriptionInput}
                placeholder="Add a description for this pin..."
                value={pinDescription}
                onChangeText={setPinDescription}
                multiline
                numberOfLines={3}
                textAlignVertical="top"
              />
            </ScrollView>
            
            {/* Fixed Bottom Action Buttons */}
            <View style={journalStyles.buttonContainer}>
              <TouchableOpacity
                style={[journalStyles.button, journalStyles.cancelButton]}
                onPress={handleCancelPin}
              >
                <Text style={journalStyles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={[
                  journalStyles.button, 
                  journalStyles.addButton,
                  !pinPhoto && journalStyles.disabledButton
                ]}
                onPress={handleAddPin}
                disabled={!pinPhoto}
              >
                <Text style={[
                  journalStyles.addButtonText,
                  !pinPhoto && journalStyles.disabledButtonText
                ]}>Add Pin</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Pin Detail Modal */}
      <Modal
        visible={showPinDetailModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => {
          handleClosePinDetail();
        }}
      >
        <View style={journalStyles.pinDetailModalOverlay}>
          <Animated.View 
            style={[
              journalStyles.pinDetailModalContent,
              {
                transform: [{ translateY: modalTranslateY }],
                opacity: modalOpacity,
              }
            ]}
          >
            {localSelectedPin && (() => {
              const currentPin = localSelectedPin;
              if (!currentPin) return null;
              
              const icon = getCategoryIcon(currentPin.category);
              const distance = calculateDistance(location, currentPin.latitude, currentPin.longitude);
              
              // Handle different property names for image URL
              const imageUrl = (currentPin as any).photoUri || (currentPin as any).imageURL;
              
              return (
                <View style={{ flex: 1 }}>
                  {/* Fixed Header with category icon and title */}
                  <View 
                    style={[journalStyles.pinDetailHeader, { backgroundColor: icon.bg }]}
                    {...panResponder.panHandlers}
                  >
                    <View style={journalStyles.pinDetailHeaderContent}>
                      <View style={journalStyles.pinDetailIconContainer}>
                        <MaterialCommunityIcons name={icon.name as any} size={32} color={icon.color} />
                      </View>
                      <View style={journalStyles.pinDetailHeaderText}>
                        <Text style={journalStyles.pinDetailTitle}>
                          {currentPin.title || `${currentPin.category.charAt(0).toUpperCase() + currentPin.category.slice(1)} Pin`}
                        </Text>
                        {currentPin.createdAt && (
                          <Text style={journalStyles.pinDetailTime}>
                            {formatRelativeTime(currentPin.createdAt)}
                          </Text>
                        )}
                      </View>
                    </View>
                    <TouchableOpacity onPress={() => {
                      handleClosePinDetail();
                    }} style={journalStyles.closeButton}>
                      <MaterialCommunityIcons name="close" size={24} color="#fff" />
                    </TouchableOpacity>
                  </View>

                  {/* Scrollable Content */}
                  <ScrollView 
                    showsVerticalScrollIndicator={true}
                    scrollEnabled={true}
                    style={{ flex: 1 }}
                    contentContainerStyle={{ paddingBottom: 20 }}
                    nestedScrollEnabled={true}
                  >
                    {/* Photo */}
                    {imageUrl && (
                      <View style={journalStyles.pinDetailImageContainer}>
                        <Image 
                          source={{ uri: imageUrl }} 
                          style={journalStyles.pinDetailImage}
                          resizeMode="cover"
                          onError={(error) => {
                            console.log('Image load error:', error.nativeEvent.error);
                            console.log('Image URI:', imageUrl);
                          }}
                          onLoad={() => {
                            console.log('Image loaded successfully:', imageUrl);
                          }}
                        />
                      </View>
                    )}

                    {/* Content */}
                    <View style={journalStyles.pinDetailContent}>
                      <Text style={journalStyles.pinDetailLabel}>Description</Text>
                      <Text style={journalStyles.pinDetailDescription}>
                        {currentPin.description || 'No description provided'}
                      </Text>

                      {/* Creator Info */}
                      {(currentPin as any).createdByUsername && (
                        <View style={journalStyles.pinDetailCreatorSection}>
                          <Text style={journalStyles.pinDetailCreatorLabel}>Created by</Text>
                          <View style={journalStyles.pinDetailCreatorInfo}>
                            {(currentPin as any).createdByProfileImage ? (
                              <Image 
                                source={{ uri: (currentPin as any).createdByProfileImage }} 
                                style={journalStyles.pinDetailCreatorAvatar}
                              />
                            ) : (
                              <View style={journalStyles.pinDetailCreatorAvatarPlaceholder}>
                                <MaterialCommunityIcons name="account" size={24} color="#8E8E93" />
                              </View>
                            )}
                            <Text style={journalStyles.pinDetailCreatorName}>{(currentPin as any).createdByUsername}</Text>
                          </View>
                        </View>
                      )}
                    </View>
                  </ScrollView>

                  {/* Fixed Bottom Button */}
                  <View style={journalStyles.pinDetailBottomSection}>
                    {distance && (
                      <Text style={journalStyles.pinDetailDistanceButton}>{distance} away</Text>
                    )}
                    <TouchableOpacity 
                      style={[journalStyles.pinDetailDirectionsButton, { backgroundColor: icon.bg }]}
                      onPress={async () => {
                        const success = await handleNavigateToPin(location, currentPin.latitude, currentPin.longitude);
                        if (success) {
                          setShowPinDetailModal(false);
                        }
                      }}
                    >
                      <Text style={journalStyles.pinDetailDirectionsButtonText}>Get Directions</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })()}
          </Animated.View>
        </View>
      </Modal>
    </View>
  );
};