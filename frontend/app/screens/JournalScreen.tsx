import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, TextInput, StyleSheet, ActivityIndicator, Modal, TouchableOpacity, ScrollView, FlatList, Image, PanResponder, Animated, RefreshControl, KeyboardAvoidingView, Platform } from 'react-native';
import type { LocationObjectCoords } from 'expo-location';
import MapView, { Marker } from 'react-native-maps';
import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import * as Location from 'expo-location';
import { calculateDistance, handleNavigateToPin, formatRelativeTime } from '../../utils/helpers';
import { journalStyles } from '../../styles/journalStyles';
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
  total_conversations?: number;
  all_messages?: string[];
  all_responses?: string[];
  conversations?: ConversationEntry[];
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
  
  // Edit mode states
  const [isEditing, setIsEditing] = useState(false);
  const [editableMessage, setEditableMessage] = useState('');
  const [editableResponse, setEditableResponse] = useState('');
  const [isSaving, setIsSaving] = useState(false);

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
      console.log('🔍 Loading conversation data...');
      
      // Debug: Check user info first
      const debugResponse = await apiClient.get('/journal/debug/user');
      console.log('🔍 Debug user info:', debugResponse.data);
      
      // Load conversation locations for map
      const locationsResponse = await apiClient.get('/journal/locations');
      console.log('🗺️ Locations response:', locationsResponse.data);
      if (locationsResponse.data && locationsResponse.data.locations) {
        setConversationLocations(locationsResponse.data.locations);
      }

      // Load journal entries by date from journal collection
      const journalResponse = await apiClient.get('/journal/entries');
      console.log('📖 Journal entries response:', journalResponse.data);
      if (journalResponse.data && journalResponse.data.journal_entries) {
        const journalData = journalResponse.data.journal_entries;
        
        // Transform journal entries into daily format
        const dailyConversationsData: DailyConversation[] = Object.entries(journalData)
          .map(([date, entries]: [string, any]) => {
            const entryArray = Array.isArray(entries) ? entries : [];
            
            // Transform journal entries into the format expected by the UI
            const conversations = entryArray.map((entry: any) => ({
              message: entry.summary || "Journal Entry",
              response: entry.diary || entry.summary || "No summary available",
              timestamp: entry.timestamp || "",
              latitude: undefined,
              longitude: undefined,
              location_name: undefined,
              photo_url: entry.photoUrl,
              session_id: ""
            }));

            const locations = entryArray
              .filter((entry: any) => entry.latitude && entry.longitude)
              .map((entry: any) => ({
                latitude: entry.latitude!,
                longitude: entry.longitude!,
                location_name: entry.location_name || 'Unknown Location'
              }));

            return {
              date,
              conversations,
              totalMessages: entryArray.length,
              locations
            };
          })
          .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()); // Sort by date descending

        console.log('📅 Daily journal entries:', dailyConversationsData);
        setDailyConversations(dailyConversationsData);
      }
    } catch (error) {
      console.error('❌ Error loading journal data:', error);
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
    setIsEditing(false);
    setEditableMessage('');
    setEditableResponse('');
  };

  const handleEditPress = () => {
    if (selectedConversation) {
      setEditableMessage(selectedConversation.message);
      setEditableResponse(selectedConversation.response);
      setIsEditing(true);
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedConversation) return;
    
    setIsSaving(true);
    try {
      await apiClient.patch(`/journal/entries/${selectedConversation.timestamp}`, {
        summary: editableMessage,
        diary: editableResponse
      });
      
      // Update local state
      selectedConversation.message = editableMessage;
      selectedConversation.response = editableResponse;
      
      // Refresh the data
      await loadConversationData();
      
      setIsEditing(false);
      alert('Journal entry updated successfully!');
    } catch (error) {
      console.error('Error updating journal entry:', error);
      alert('Failed to update journal entry');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditableMessage('');
    setEditableResponse('');
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadConversationData().then(() => setRefreshing(false));
  }, []);

  const renderDailyConversationItem = ({ item }: { item: DailyConversation }) => {
    const formattedDate = new Date(item.date).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    const handleConversationPress = (conversation: ConversationEntry) => {
      // Always open modal, even without location data
      const conversationLocation: ConversationLocation = {
        id: `${item.date}_${conversation.timestamp}`,
        latitude: conversation.latitude || 0,
        longitude: conversation.longitude || 0,
        location_name: conversation.location_name || 'Journal Entry',
        message: conversation.message,
        response: conversation.response,
        photo_url: conversation.photo_url,
        timestamp: conversation.timestamp,
        date: item.date
      };
      setSelectedConversation(conversationLocation);
      setShowConversationModal(true);
    };

    return (
      <View style={styles.dailyConversationCard}>
        <View style={styles.dailyConversationHeader}>
          <Text style={styles.dailyConversationDate}>{formattedDate}</Text>
          <View style={styles.dailyConversationStats}>
            <MaterialCommunityIcons name="message-text" size={16} color="#666" />
            <Text style={styles.dailyConversationCount}>{item.totalMessages} messages</Text>
            {item.locations.length > 0 && (
              <>
                <MaterialCommunityIcons name="map-marker" size={16} color="#666" />
                <Text style={styles.dailyConversationLocations}>{item.locations.length} locations</Text>
              </>
            )}
          </View>
        </View>

        {/* Show preview of conversations */}
        <View style={styles.conversationPreviewContainer}>
          {item.conversations.slice(0, 3).map((conversation, index) => (
            <TouchableOpacity 
              key={index} 
              style={styles.conversationPreviewCard}
              onPress={() => handleConversationPress(conversation)}
              activeOpacity={0.7}
            >
              <View style={styles.conversationPreviewContent}>
                <Text style={styles.conversationPreviewMessage} numberOfLines={2}>
                  {conversation.message}
                </Text>
                <Text style={styles.conversationPreviewResponse} numberOfLines={3}>
                  {conversation.response}
                </Text>
                {conversation.location_name && (
                  <View style={styles.conversationPreviewLocation}>
                    <MaterialCommunityIcons name="map-marker" size={12} color="#999" />
                    <Text style={styles.conversationPreviewLocationText} numberOfLines={1}>
                      {conversation.location_name}
                    </Text>
                  </View>
                )}
              </View>

              {/* Image AFTER content so text always hugs the top */}
              {conversation.photo_url && (
                <Image 
                  source={{ uri: conversation.photo_url }} 
                  style={[styles.conversationPreviewImage, { marginTop: 8, marginBottom: 0 }]}
                  resizeMode="cover"
                />
              )}
            </TouchableOpacity>
          ))}
          
          {item.conversations.length > 3 && (
            <View style={styles.moreConversationsCard}>
              <MaterialCommunityIcons name="dots-horizontal" size={24} color="#999" />
              <Text style={styles.moreConversationsText}>
                +{item.conversations.length - 3} more
              </Text>
            </View>
          )}
        </View>
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
              zoomEnabled={true}
              scrollEnabled={true}
              pitchEnabled={true}
              rotateEnabled={false}
              onMapReady={() => {
                console.log('🗺️ Map is ready');
              }}
            >
              {conversationLocations.map((conversationLocation) => (
                <Marker
                  key={conversationLocation.id}
                  coordinate={{ 
                    latitude: conversationLocation.latitude, 
                    longitude: conversationLocation.longitude 
                  }}
                  onPress={() => handleMarkerPress(conversationLocation)}
                >
                  <View style={journalStyles.markerWrapper}>
                    <View style={[journalStyles.markerBubble, { backgroundColor: '#007AFF' }]}> 
                      <MaterialCommunityIcons name="message-text" size={18} color="white" />
                      {conversationLocation.total_conversations && conversationLocation.total_conversations > 1 && (
                        <View style={styles.conversationCountBadge}>
                          <Text style={styles.conversationCountText}>
                            {conversationLocation.total_conversations}
                          </Text>
                        </View>
                      )}
                    </View>
                    <View style={[journalStyles.markerPointer, { borderTopColor: '#007AFF' }]} />
                  </View>
                </Marker>
              ))}
            </MapView>
          ) : (
            // List View - Daily Conversations
            <View style={{ flex: 1 }}>
              {/* Header */}
              <View style={journalStyles.filterHeader}>
                <Text style={styles.headerTitle}>Your Journal</Text>
                <Text style={styles.headerSubtitle}>
                  Conversations from your cultural adventures
                </Text>
              </View>

              {/* Daily Conversations List */}
              <FlatList
                data={dailyConversations}
                renderItem={renderDailyConversationItem}
                keyExtractor={(item) => item.date}
                refreshControl={
                  <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
                }
                showsVerticalScrollIndicator={false}
                contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
                ListEmptyComponent={
                  <View style={journalStyles.emptyContainer}>
                    <MaterialCommunityIcons name="message-text-outline" size={48} color="#8E8E93" />
                    <Text style={journalStyles.emptyText}>No conversations yet</Text>
                    <Text style={journalStyles.emptySubtext}>
                      Start chatting with Hermes to see your journal entries here
                    </Text>
                  </View>
                }
              />
            </View>
          )}
        </>
      )}
      
      {/* Conversation Detail Modal */}
      <Modal
        visible={showConversationModal}
        animationType="slide"
        transparent={true}
        onRequestClose={handleCloseConversationDetail}
      >
        <KeyboardAvoidingView 
          style={{ flex: 1 }} 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
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
              {selectedConversation && (
                <View style={{ flex: 1 }}>
                {/* Fixed Header */}
                <View 
                  style={[journalStyles.pinDetailHeader, { backgroundColor: '#007AFF' }]}
                  {...panResponder.panHandlers}
                >
                  <View style={journalStyles.pinDetailHeaderContent}>
                    <View style={journalStyles.pinDetailIconContainer}>
                      <MaterialCommunityIcons name="message-text" size={32} color="white" />
                    </View>
                    <View style={journalStyles.pinDetailHeaderText}>
                      <Text style={journalStyles.pinDetailTitle}>
                        {selectedConversation.location_name || 'Journal Entry'}
                      </Text>
                      <Text style={journalStyles.pinDetailTime}>
                        {formatRelativeTime(selectedConversation.timestamp)}
                      </Text>
                    </View>
                  </View>
                  <TouchableOpacity 
                    onPress={handleCloseConversationDetail} 
                    style={journalStyles.closeButton}
                  >
                    <MaterialCommunityIcons name="close" size={24} color="#fff" />
                  </TouchableOpacity>
                </View>

                {/* Scrollable Content */}
                <ScrollView 
                  showsVerticalScrollIndicator={true}
                  style={{ flex: 1 }}
                  contentContainerStyle={{ paddingBottom: 20 }}
                >
                  {/* Photo */}
                  {selectedConversation.photo_url && (
                    <View style={journalStyles.pinDetailImageContainer}>
                      <Image 
                        source={{ uri: selectedConversation.photo_url }} 
                        style={journalStyles.pinDetailImage}
                        resizeMode="cover"
                      />
                    </View>
                  )}

                  {/* Conversation Content */}
                  <View style={journalStyles.pinDetailContent}>
                    {selectedConversation.conversations && selectedConversation.conversations.length > 1 ? (
                      // Multiple conversations for the day
                      <>
                        <Text style={journalStyles.pinDetailLabel}>
                          Daily Conversations ({selectedConversation.total_conversations} messages)
                        </Text>
                        <ScrollView style={{ maxHeight: 400 }}>
                          {selectedConversation.conversations.map((conversation, index) => (
                            <View key={index} style={styles.individualConversationCard}>
                              <View style={styles.conversationHeader}>
                                <Text style={styles.conversationIndex}>Message {index + 1}</Text>
                                <Text style={styles.conversationTime}>
                                  {new Date(conversation.timestamp).toLocaleTimeString()}
                                </Text>
                              </View>
                              <Text style={journalStyles.pinDetailLabel}>Title</Text>
                              <Text style={styles.conversationMessage}>{conversation.message}</Text>
                              <Text style={journalStyles.pinDetailLabel}>Diary Entry</Text>
                              <Text style={styles.conversationResponse}>{conversation.response}</Text>
                            </View>
                          ))}
                        </ScrollView>
                      </>
                    ) : (
                      // Single conversation
                      <>
                        <Text style={journalStyles.pinDetailLabel}>Title</Text>
                        {isEditing ? (
                          <TextInput
                            style={styles.editTextInput}
                            value={editableMessage}
                            onChangeText={setEditableMessage}
                            multiline
                            placeholder="Enter title..."
                          />
                        ) : (
                          <Text style={journalStyles.pinDetailDescription}>
                            {selectedConversation.message}
                          </Text>
                        )}

                        <Text style={journalStyles.pinDetailLabel}>Diary Entry</Text>
                        {isEditing ? (
                          <TextInput
                            style={styles.editTextInput}
                            value={editableResponse}
                            onChangeText={setEditableResponse}
                            multiline
                            placeholder="Enter diary entry..."
                          />
                        ) : (
                          <Text style={journalStyles.pinDetailDescription}>
                            {selectedConversation.response}
                          </Text>
                        )}
                      </>
                    )}
                  </View>
                </ScrollView>

                {/* Fixed Bottom Buttons */}
                <View style={journalStyles.pinDetailBottomSection}>
                  {isEditing ? (
                    <>
                      <TouchableOpacity 
                        style={[journalStyles.pinDetailDirectionsButton, { backgroundColor: '#34C759', marginRight: 8 }]}
                        onPress={handleSaveEdit}
                        disabled={isSaving}
                      >
                        <Text style={journalStyles.pinDetailDirectionsButtonText}>
                          {isSaving ? 'Saving...' : 'Save'}
                        </Text>
                      </TouchableOpacity>
                      <TouchableOpacity 
                        style={[journalStyles.pinDetailDirectionsButton, { backgroundColor: '#8E8E93' }]}
                        onPress={handleCancelEdit}
                        disabled={isSaving}
                      >
                        <Text style={journalStyles.pinDetailDirectionsButtonText}>Cancel</Text>
                      </TouchableOpacity>
                    </>
                  ) : (
                    <>
                      <TouchableOpacity 
                        style={[journalStyles.pinDetailDirectionsButton, { backgroundColor: '#007AFF', marginRight: 8 }]}
                        onPress={handleEditPress}
                      >
                        <Text style={journalStyles.pinDetailDirectionsButtonText}>Edit</Text>
                      </TouchableOpacity>
                      {selectedConversation.latitude && selectedConversation.longitude && location && (
                        <>
                          <Text style={journalStyles.pinDetailDistanceButton}>
                            {calculateDistance(location, selectedConversation.latitude, selectedConversation.longitude)} away
                          </Text>
                          <TouchableOpacity 
                            style={[journalStyles.pinDetailDirectionsButton, { backgroundColor: '#007AFF' }]}
                            onPress={async () => {
                              const success = await handleNavigateToPin(
                                location, 
                                selectedConversation.latitude, 
                                selectedConversation.longitude
                              );
                              if (success) {
                                setShowConversationModal(false);
                              }
                            }}
                          >
                            <Text style={journalStyles.pinDetailDirectionsButtonText}>Get Directions</Text>
                          </TouchableOpacity>
                        </>
                      )}
                    </>
                  )}
                </View>
              </View>
            )}
            </Animated.View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#666',
  },
  dailyConversationCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  dailyConversationHeader: {
    marginBottom: 12,
  },
  dailyConversationDate: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  dailyConversationStats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dailyConversationCount: {
    fontSize: 14,
    color: '#666',
    marginRight: 8,
  },
  dailyConversationLocations: {
    fontSize: 14,
    color: '#666',
  },
  conversationPreviewScroll: {
    marginTop: 8,
  },
  conversationPreviewContainer: {
    marginTop: 8,
    gap: 12,
  },
  conversationPreviewCard: {
    width: '100%',
    minHeight: 250,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e9ecef',
    justifyContent: 'flex-start',
    alignItems: 'flex-start',
  },
  conversationPreviewImage: {
    width: '100%',
    height: 80,
    borderRadius: 6,
    marginBottom: 0,
  },
  conversationPreviewContent: {
    width: '100%',
  },
  conversationPreviewMessage: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
    marginBottom: 4,
  },
  conversationPreviewResponse: {
    fontSize: 13,
    color: '#666',
    marginBottom: 8,
  },
  conversationPreviewLocation: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  conversationPreviewLocationText: {
    fontSize: 12,
    color: '#999',
    flex: 1,
  },
  moreConversationsCard: {
    width: 120,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#e9ecef',
    borderStyle: 'dashed',
  },
  moreConversationsText: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
    textAlign: 'center',
  },
  conversationCountBadge: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#FF3B30',
    borderRadius: 10,
    width: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'white',
  },
  conversationCountText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: 'white',
  },
  individualConversationCard: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e9ecef',
  },
  conversationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  conversationIndex: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  conversationTime: {
    fontSize: 12,
    color: '#666',
  },
  conversationMessage: {
    fontSize: 14,
    color: '#333',
    marginBottom: 8,
    lineHeight: 20,
  },
  conversationResponse: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  editTextInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    color: '#333',
    backgroundColor: '#fff',
    minHeight: 80,
    textAlignVertical: 'top',
  },
});
