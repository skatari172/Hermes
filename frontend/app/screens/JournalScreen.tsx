import React, { useEffect, useState, useCallback } from 'react';
import { Dimensions } from 'react-native';
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
  diarySummary?: string;
  images?: string[];
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
  const [fullPageMode, setFullPageMode] = useState(false);
  
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

      // Also fetch centralized per-day bundles (images + summary) from entries collection
      let dailyEntriesMap: Record<string, any> = {};
      try {
        const entriesResp = await apiClient.get('/journal/daily_entries');
        console.log('🗂️ Daily entries (entries collection) response:', entriesResp.data);
        if (entriesResp.data && entriesResp.data.daily_entries) {
          dailyEntriesMap = entriesResp.data.daily_entries;
        }
      } catch (e) {
        console.warn('Could not fetch /journal/daily_entries for list view images:', e);
      }

      if (journalResponse.data && journalResponse.data.journal_entries) {
        const journalData = journalResponse.data.journal_entries;
        
        // Transform journal entries into daily format
        const normalizeUrl = (url: string | undefined | null) => {
          if (!url) return null;
          const trimmed = String(url || '').trim();
          if (!trimmed) return null;
          // Filter out known placeholder tokens that may come from older DB entries
          if (trimmed.toLowerCase().includes('placeholder_image_url')) return null;
          if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed;
          // Make sure baseURL is present
          const base = apiClient.defaults.baseURL || '';
          if (trimmed.startsWith('/')) return `${base}${trimmed}`;
          return `${base}/${trimmed}`;
        };

        const dailyConversationsData: DailyConversation[] = Object.entries(journalData)
          .map(([date, entries]: [string, any]) => {
            const entryArray = Array.isArray(entries) ? entries : [];
            
            // Transform journal entries into the format expected by the UI
            const conversations = entryArray.map((entry: any) => ({
              message: entry.summary || "Journal Entry",
              response: entry.diary || entry.summary || "No summary available",
              timestamp: entry.timestamp || "",
              latitude: entry.latitude,
              longitude: entry.longitude,
              location_name: entry.location_name,
              // Support both camelCase and snake_case keys from backend
              photo_url: normalizeUrl(entry.photoUrl || entry.photo_url || entry.photo) || undefined,
              session_id: entry.session_id || ""
            }));

            const locations = entryArray
              .filter((entry: any) => entry.latitude && entry.longitude)
              .map((entry: any) => ({
                latitude: entry.latitude!,
                longitude: entry.longitude!,
                location_name: entry.location_name || 'Unknown Location'
              }));

            // Collect images for the day.
            // Prefer images provided by the centralized `entries` collection (which are normalized by the backend)
            // Fallback to collecting from the journal entries if none are available.
            let images: string[] = [];
            try {
              const bundle = dailyEntriesMap[date];
              if (bundle && Array.isArray(bundle.images) && bundle.images.length > 0) {
                // bundle.images may already contain normalized absolute URLs from backend
                images = bundle.images.map((u: string) => normalizeUrl(u)).filter(Boolean) as string[];
              }
            } catch (e) {
              // ignore and fall back
            }

            // Helper: scan an entry for any photo-like fields (be permissive to handle typos)
            const extractPhotoFromEntry = (ent: any) => {
              if (!ent || typeof ent !== 'object') return null;
              const candidates: {k:string;v:any}[] = [];
              for (const k of Object.keys(ent)) {
                if (/photo/i.test(k) && ent[k]) {
                  candidates.push({k, v: ent[k]});
                }
              }
              // Prefer common keys first
              const preferred = candidates.find(c => ["photo_url","photoUrl","photo"].includes(c.k));
              const pick = preferred || candidates[0];
              if (!pick) return null;
              return normalizeUrl(pick.v) || null;
            };

            if (!images || images.length === 0) {
              // Build from journal entries, but be permissive about key names
              const found: string[] = [];
              for (const e of entryArray) {
                const p = extractPhotoFromEntry(e);
                // Logging photo-like fields for debugging
                const rawPhotoFields: Record<string, any> = {};
                for (const k of Object.keys(e)) {
                  if (/photo/i.test(k)) rawPhotoFields[k] = e[k];
                }
                if (Object.keys(rawPhotoFields).length) {
                  console.log(`🔎 Entry photo fields for date ${date}:`, rawPhotoFields);
                }
                if (p) found.push(p);
              }
              images = found.filter(Boolean);
            }

            console.log(`📸 Final images for ${date}:`, images);

            // Prefer an existing diary field (current generated summary). If none, fall back to concatenated summaries.
            const diaryEntry = entryArray.find((e: any) => e.diary && String(e.diary).trim());
            const diarySummary = diaryEntry
              ? diaryEntry.diary
              : entryArray.map((e: any) => e.summary || e.response || '').filter(Boolean).join('\n\n') || '';

            return {
              date,
              conversations,
              totalMessages: entryArray.length,
              locations,
              diarySummary,
              images
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

  const handleMarkerPress = async (conversationLocation: ConversationLocation) => {
    // Only fetch the latest diary summary for the date and attach it to the
    // selectedConversation. Do NOT modify photos or conversation arrays here.
    try {
      if (conversationLocation && conversationLocation.date) {
        try {
          const resp = await apiClient.get('/journal/daily_entries', { params: { date: conversationLocation.date } });
          // Expect backend to return { <date>: { entries, summary, images } }
          const bundle = resp.data && (resp.data[conversationLocation.date] || resp.data[Object.keys(resp.data)[0]]);
          if (bundle) {
            // Prefer bundle.summary (the generated diary) for the modal's daily summary
            if (bundle.summary) {
              conversationLocation.response = bundle.summary;
            } else if (Array.isArray(bundle.entries) && bundle.entries.length > 0) {
              // Fallback: prefer any diary field on entries, then summary, then response
              const diaryEntry = bundle.entries.find((e: any) => e && (e.diary || e.summary || e.response));
              if (diaryEntry) {
                conversationLocation.response = diaryEntry.diary || diaryEntry.summary || diaryEntry.response || conversationLocation.response;
              }
            }
          }
        } catch (e) {
          console.warn('Could not fetch daily_entries for marker:', e);
        }
      }

      // Open modal without touching photo fields
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
    } catch (err) {
      console.error('Error handling marker press:', err);
      // Fallback to original behaviour
      setSelectedConversation(conversationLocation);
      setShowConversationModal(true);
    }
  };

  const handleCloseConversationDetail = () => {
    setShowConversationModal(false);
    setSelectedConversation(null);
    setIsEditing(false);
    setEditableMessage('');
    setEditableResponse('');
    setFullPageMode(false);
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

  // Photos gallery renderer moved to component scope so it can be reused
  const IMAGE_SIZE = Math.floor((Dimensions.get('window').width - 64) / 3);

  const renderPhotosGallery = (convs: any[] | undefined) => {
    if (!convs || convs.length === 0) return null;
    // convs may be array of url strings or conversation objects with photo_url
    const imgs: string[] = convs.map((c: any) => typeof c === 'string' ? c : (c.photo_url || c.photoUrl || c.photo)).filter(Boolean);
    if (!imgs.length) return null;

    return (
      <>
        <Text style={{ fontSize: 16, fontWeight: '600', color: '#007AFF', marginTop: 20, marginBottom: 8 }}>Photos</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' }}>
          {imgs.map((u, idx) => (
            <Image
              key={idx}
              source={{ uri: u }}
              style={{ width: IMAGE_SIZE, height: IMAGE_SIZE * 0.75, borderRadius: 8, marginBottom: 8 }}
            />
          ))}
        </View>
      </>
    );
  };

  const renderDailyConversationItem = ({ item }: { item: DailyConversation }) => {
    const formattedDate = new Date(item.date).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    const openDayView = (day: DailyConversation) => {
      // Construct a ConversationLocation-like object containing the day's details
      const convLoc: ConversationLocation = {
        id: `${day.date}_day`,
        latitude: 0,
        longitude: 0,
        location_name: `Journal for ${day.date}`,
        message: day.conversations && day.conversations.length > 0 ? day.conversations[0].message : 'Journal Day',
        response: day.diarySummary || '',
        photo_url: day.images && day.images.length > 0 ? day.images[0] : undefined,
        timestamp: day.conversations && day.conversations[0] ? day.conversations[0].timestamp : '',
        date: day.date,
        total_conversations: day.totalMessages,
        conversations: day.conversations,
        all_messages: day.conversations ? day.conversations.map(c => c.message) : [],
        all_responses: day.conversations ? day.conversations.map(c => c.response) : [],
      };

      setSelectedConversation(convLoc);
      setFullPageMode(true);
      setShowConversationModal(true);
    };

    

    return (
  <TouchableOpacity activeOpacity={0.95} onPress={() => openDayView(item)}>
        <View style={styles.dailyConversationCard}>
        <View style={styles.dailyConversationHeader}>
          <Text style={styles.dailyConversationDate}>{formattedDate}</Text>
        </View>

        {/* Show centralized diary summary for the day + thumbnails of all images */}
        <View style={styles.conversationPreviewContainer}>
          {item.diarySummary ? (
            <Text style={styles.dailyDiarySummary} numberOfLines={5}>{item.diarySummary}</Text>
          ) : (
            <Text style={styles.noDiaryText}>No summary yet for this day</Text>
          )}

          {item.images && item.images.length > 0 && (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 12 }}>
                  {item.images.map((img, idx) => {
                    return (
                      <TouchableOpacity
                        key={`${item.date}_img_${idx}`}
                        onPress={() => openDayView(item)}
                        activeOpacity={0.8}
                        style={{ marginRight: 8 }}
                      >
                        <Image
                          source={{ uri: img }}
                          style={styles.dailyThumbnail}
                          resizeMode="cover"
                        />
                      </TouchableOpacity>
                    );
                  })}
            </ScrollView>
          )}
        </View>
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
                    {/* Show image-based pin */}
                    <View style={journalStyles.markerBubbleLarge}>
                      {conversationLocation.photo_url ? (
                        <Image source={{ uri: conversationLocation.photo_url }} style={journalStyles.markerImage} />
                      ) : (
                        <View style={[journalStyles.markerImage, { backgroundColor: '#E5E5EA', justifyContent: 'center', alignItems: 'center' }]}>
                          <MaterialCommunityIcons name="image-outline" size={24} color="#8E8E93" />
                        </View>
                      )}
                    </View>
                    {conversationLocation.total_conversations && conversationLocation.total_conversations > 1 && (
                      <View style={journalStyles.markerBadge}>
                        <Text style={[styles.conversationCountText, { fontSize: 10 }]}>
                          {conversationLocation.total_conversations}
                        </Text>
                      </View>
                    )}
                    <View style={[journalStyles.markerPointer, { borderTopColor: 'transparent' }]} />
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
                fullPageMode ? { height: '100%', borderTopLeftRadius: 0, borderTopRightRadius: 0 } : {},
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
                          {selectedConversation.date ? new Date(selectedConversation.date).toLocaleDateString() : formatRelativeTime(selectedConversation.timestamp)}
                        </Text>
                      </View>
                    </View>
                    <TouchableOpacity 
                      onPress={() => {
                        handleCloseConversationDetail();
                        setFullPageMode(false);
                      }} 
                      style={journalStyles.closeButton}
                    >
                      <MaterialCommunityIcons name="close" size={24} color="#fff" />
                    </TouchableOpacity>
                  </View>

                  {fullPageMode ? (
                    // Full-day scrollable page view: show only photo(s) and Daily Summary (no individual messages)
                    <ScrollView showsVerticalScrollIndicator={true} style={{ flex: 1 }} contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
                      {selectedConversation.photo_url && (
                        <View style={{ height: 220, marginBottom: 12 }}>
                          <Image source={{ uri: selectedConversation.photo_url }} style={{ width: '100%', height: '100%', borderRadius: 12 }} resizeMode="cover" />
                        </View>
                      )}

                      <Text style={{ fontSize: 16, fontWeight: '600', color: '#007AFF', marginBottom: 8 }}>Daily Summary</Text>
                      <Text style={{ fontSize: 15, color: '#333', lineHeight: 22 }}>{selectedConversation.response || selectedConversation.all_responses?.join('\n\n') || 'No summary available.'}</Text>

                      {renderPhotosGallery(selectedConversation.conversations)}
                    </ScrollView>
                  ) : (
                    // Original (per-conversation) modal content (photo under header removed)
                    <ScrollView 
                      showsVerticalScrollIndicator={true}
                      style={{ flex: 1 }}
                      contentContainerStyle={{ paddingBottom: 20 }}
                    >
                      {/* Conversation Content */}
                      <View style={journalStyles.pinDetailContent}>
                        {/* In card/modal view we show only the Daily Summary and Photos (no individual messages) */}
                        <Text style={journalStyles.pinDetailLabel}>Daily Summary</Text>
                        {/* View Diary button: switch to list view and open full-page day view */}
                        <TouchableOpacity
                            onPress={() => {
                            // Try to find the actual day object from loaded dailyConversations and open that
                            const dateKey = selectedConversation.date || (selectedConversation.timestamp ? selectedConversation.timestamp.split('T')[0] : '');
                            const dayEntry = dailyConversations.find(d => d.date === dateKey);
                            if (dayEntry) {
                              const dayObj: any = {
                                id: `${dayEntry.date}_day`,
                                latitude: 0,
                                longitude: 0,
                                location_name: `Journal for ${dayEntry.date}`,
                                message: dayEntry.conversations && dayEntry.conversations.length > 0 ? dayEntry.conversations[0].message : 'Journal Day',
                                response: dayEntry.diarySummary || '',
                                photo_url: dayEntry.images && dayEntry.images.length > 0 ? dayEntry.images[0] : undefined,
                                timestamp: dayEntry.conversations && dayEntry.conversations[0] ? dayEntry.conversations[0].timestamp : '',
                                date: dayEntry.date,
                                total_conversations: dayEntry.totalMessages,
                                conversations: dayEntry.conversations || [],
                                all_messages: dayEntry.conversations ? dayEntry.conversations.map((c:any)=>c.message) : [],
                                all_responses: dayEntry.conversations ? dayEntry.conversations.map((c:any)=>c.response) : [],
                              };
                              setViewMode('list');
                              setSelectedConversation(dayObj);
                              setFullPageMode(true);
                              setShowConversationModal(true);
                            } else {
                              // Fallback: construct from selectedConversation
                              const fallbackDate = dateKey;
                              const dayObj: any = {
                                id: `${fallbackDate}_day`,
                                latitude: 0,
                                longitude: 0,
                                location_name: selectedConversation.location_name || `Journal for ${fallbackDate}`,
                                message: selectedConversation.message || 'Journal Day',
                                response: selectedConversation.response || '',
                                photo_url: selectedConversation.photo_url,
                                timestamp: selectedConversation.timestamp || '',
                                date: fallbackDate,
                                total_conversations: selectedConversation.total_conversations || (selectedConversation.conversations ? selectedConversation.conversations.length : 0),
                                conversations: selectedConversation.conversations || [],
                                all_messages: selectedConversation.all_messages || [],
                                all_responses: selectedConversation.all_responses || [],
                              };
                              setViewMode('list');
                              setSelectedConversation(dayObj);
                              setFullPageMode(true);
                              setShowConversationModal(true);
                            }
                            }}
                            style={{ marginTop: 12, alignSelf: 'flex-start', backgroundColor: '#007AFF', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 8 }}
                          >
                            <Text style={{ color: '#fff', fontWeight: '600' }}>View Diary</Text>
                          </TouchableOpacity>
                        {selectedConversation.conversations && selectedConversation.conversations.length > 0 && (
                          <>
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '#007AFF', marginTop: 20, marginBottom: 8 }}>Photos</Text>
                              <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' }}>
                                {selectedConversation.conversations.map((c, idx) => {
                                  const src = c && (((c as any).photo_url) || ((c as any).photoUrl) || ((c as any).photo));
                                  if (!src) return null;
                                  return (
                                    <Image key={idx} source={{ uri: src }} style={{ width: IMAGE_SIZE, height: IMAGE_SIZE * 0.75, borderRadius: 8, marginBottom: 8 }} />
                                  );
                                })}
                              </View>
                          </>
                        )}
                      </View>
                    </ScrollView>
                  )}
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
  dailyDiarySummary: {
    fontSize: 15,
    color: '#333',
    lineHeight: 20,
    marginBottom: 8,
  },
  noDiaryText: {
    fontSize: 13,
    color: '#8E8E93',
  },
  dailyThumbnail: {
    width: 120,
    height: 80,
    borderRadius: 8,
    backgroundColor: '#e9ecef',
  },
});
