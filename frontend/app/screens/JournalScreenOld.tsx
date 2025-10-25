import React, { useEffect, useState, useRef, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Modal, TouchableOpacity, ScrollView, FlatList, Image, PanResponder, Animated, Platform, RefreshControl } from 'react-native';
import type { LocationObjectCoords } from 'expo-location';
import MapView, { Marker } from 'react-native-maps';
import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import * as Location from 'expo-location';
import { calculateDistance, handleNavigateToPin, getCategoryIcon, formatRelativeTime, distanceMeters, formatDistance } from '../../utils/helpers';
import { journalStyles } from '../../styles/journalStyles';
import { pinsStyles } from '../../styles/pinsStyles';
import { useNavigation } from '@react-navigation/native';
import apiClient from '../../api/apiClient';

// Define conversation types
interface ConversationEntry {
  message: string;
  response: string;
  timestamp: string;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  photo_url?: string;
  session_id: string;
}

interface DailyConversation {
  date: string;
  conversations: ConversationEntry[];
  totalMessages: number;
  locations: Array<{
    latitude: number;
    longitude: number;
    location_name: string;
  }>;
}

interface ConversationLocation {
  id: string;
  latitude: number;
  longitude: number;
  location_name: string;
  message: string;
  response: string;
  photo_url?: string;
  timestamp: string;
  date: string;
}

export default function JournalScreen() {
  const [location, setLocation] = useState<LocationObjectCoords | null>(null);
  const [loading, setLoading] = useState(true);
  
  // View mode state for toggle between map and list
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  
  // Conversation data states
  const [refreshing, setRefreshing] = useState(false);
  const [conversationLocations, setConversationLocations] = useState<ConversationLocation[]>([]);
  const [dailyConversations, setDailyConversations] = useState<DailyConversation[]>([]);
  
  const [mapRef, setMapRef] = useState<MapView | null>(null);
  
  // Navigation for refresh functionality
  const navigation = useNavigation();
  
  // Conversation detail modal states
  const [showConversationModal, setShowConversationModal] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<ConversationLocation | null>(null);

  // Swipe gesture states for modal
  const [modalTranslateY] = useState(new Animated.Value(0));
  const [modalOpacity] = useState(new Animated.Value(1));

  // Pan responder for swipe-to-dismiss functionality on modal
  const panResponder = PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: (evt, gestureState) => {
      return Math.abs(gestureState.dy) > Math.abs(gestureState.dx) && gestureState.dy > 10;
    },
    onPanResponderGrant: () => {},
    onPanResponderMove: (evt, gestureState) => {
      if (gestureState.dy >= 0) {
        modalTranslateY.setValue(gestureState.dy);
        const opacity = Math.max(0.3, 1 - (gestureState.dy / 300));
        modalOpacity.setValue(opacity);
      }
    },
    onPanResponderRelease: (evt, gestureState) => {
      if (gestureState.dy > 250 || gestureState.vy > 1.5) {
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
          handleCloseConversationDetail();
          modalTranslateY.setValue(0);
          modalOpacity.setValue(1);
        });
      } else {
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

  // Load conversation data on component mount
  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setLoading(false);
        return;
      }
      let loc = await Location.getCurrentPositionAsync({});
      setLocation(loc.coords);
      
      // Load conversation data
      await loadConversationData();
      setLoading(false);
    })();
  }, []);

  // Refresh on navigation focus
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      if (conversationLocations.length > 0 || dailyConversations.length > 0) {
        loadConversationData();
      }
    });
    return unsubscribe;
  }, [navigation, conversationLocations.length, dailyConversations.length]);

  const loadConversationData = async () => {
    try {
      // Load conversation locations for map
      const locationsResponse = await apiClient.get('/journal/locations');
      if (locationsResponse.data && locationsResponse.data.locations) {
        setConversationLocations(locationsResponse.data.locations);
      }

      // Load daily conversations for list view
      const conversationsResponse = await apiClient.get('/journal/conversations');
      if (conversationsResponse.data && conversationsResponse.data.conversations) {
        const conversationsData = conversationsResponse.data.conversations;
        
        // Group conversations by date and create daily conversation objects
        const dailyConversationsData: DailyConversation[] = Object.entries(conversationsData)
          .map(([date, conversations]: [string, any]) => {
            const conversationArray = Array.isArray(conversations) ? conversations : [];
            const locations = conversationArray
              .filter((conv: ConversationEntry) => conv.latitude && conv.longitude)
              .map((conv: ConversationEntry) => ({
                latitude: conv.latitude!,
                longitude: conv.longitude!,
                location_name: conv.location_name || 'Unknown Location'
              }));

            return {
              date,
              conversations: conversationArray,
              totalMessages: conversationArray.length,
              locations
            };
          })
          .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()); // Sort by date descending

        setDailyConversations(dailyConversationsData);
      }
    } catch (error) {
      console.error('Error loading conversation data:', error);
    }
  };

  const handleMarkerPress = (conversationLocation: ConversationLocation) => {
    setSelectedConversation(conversationLocation);
    setShowConversationModal(true);
    
    // Zoom to the selected location
    if (mapRef) {
      const camera = {
        center: {
          latitude: conversationLocation.latitude - 1.3e-3,
          longitude: conversationLocation.longitude,
        },
        zoom: 18,
        heading: 0,
        pitch: 0,
      };
      
      mapRef.animateCamera(camera, { duration: 1000 });
    }
  };

  const handleCloseConversationDetail = () => {
    setShowConversationModal(false);
    setSelectedConversation(null);
  };

  const renderDailyConversationItem = ({ item }: { item: DailyConversation }) => {
    const formattedDate = new Date(item.date).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    const handleConversationPress = (conversation: ConversationEntry) => {
      if (conversation.latitude && conversation.longitude) {
        const conversationLocation: ConversationLocation = {
          id: `${item.date}_${conversation.timestamp}`,
          latitude: conversation.latitude,
          longitude: conversation.longitude,
          location_name: conversation.location_name || 'Unknown Location',
          message: conversation.message,
          response: conversation.response,
          photo_url: conversation.photo_url,
          timestamp: conversation.timestamp,
          date: item.date
        };
        setSelectedConversation(conversationLocation);
        setShowConversationModal(true);
      }
    };

    return (
      <View style={journalStyles.dailyConversationCard}>
        <View style={journalStyles.dailyConversationHeader}>
          <Text style={journalStyles.dailyConversationDate}>{formattedDate}</Text>
          <View style={journalStyles.dailyConversationStats}>
            <MaterialCommunityIcons name="message-text" size={16} color="#666" />
            <Text style={journalStyles.dailyConversationCount}>{item.totalMessages} messages</Text>
            {item.locations.length > 0 && (
              <>
                <MaterialCommunityIcons name="map-marker" size={16} color="#666" />
                <Text style={journalStyles.dailyConversationLocations}>{item.locations.length} locations</Text>
              </>
            )}
          </View>
        </View>

        {/* Show preview of conversations */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={journalStyles.conversationPreviewScroll}>
          {item.conversations.slice(0, 3).map((conversation, index) => (
            <TouchableOpacity 
              key={index} 
              style={journalStyles.conversationPreviewCard}
              onPress={() => handleConversationPress(conversation)}
              activeOpacity={0.7}
            >
              {conversation.photo_url && (
                <Image 
                  source={{ uri: conversation.photo_url }} 
                  style={journalStyles.conversationPreviewImage}
                  resizeMode="cover"
                />
              )}
              <View style={journalStyles.conversationPreviewContent}>
                <Text style={journalStyles.conversationPreviewMessage} numberOfLines={2}>
                  {conversation.message}
                </Text>
                <Text style={journalStyles.conversationPreviewResponse} numberOfLines={3}>
                  {conversation.response}
                </Text>
                {conversation.location_name && (
                  <View style={journalStyles.conversationPreviewLocation}>
                    <MaterialCommunityIcons name="map-marker" size={12} color="#999" />
                    <Text style={journalStyles.conversationPreviewLocationText} numberOfLines={1}>
                      {conversation.location_name}
                    </Text>
                  </View>
                )}
              </View>
            </TouchableOpacity>
          ))}
          
          {item.conversations.length > 3 && (
            <View style={journalStyles.moreConversationsCard}>
              <MaterialCommunityIcons name="dots-horizontal" size={24} color="#999" />
              <Text style={journalStyles.moreConversationsText}>
                +{item.conversations.length - 3} more
              </Text>
            </View>
          )}
        </ScrollView>
      </View>
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