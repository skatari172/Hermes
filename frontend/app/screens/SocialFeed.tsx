import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, RefreshControl } from 'react-native';
import { PostList, PostForm } from '../components/socialcomponents';
import apiClient from '../../api/apiClient';
import { auth } from '../../config/firebase';

// Define types based on journal data structure
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
  total_conversations: number;
  location_name: string;
}

interface SocialPost {
  id: string;
  user: {
    name: string;
    avatar?: string;
    username: string;
  };
  content: string;
  image?: string;
  timestamp: string;
  likes: number;
  comments: number;
  isLiked: boolean;
  location?: string;
}

export default function SocialFeed() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showPostForm, setShowPostForm] = useState(false);

  // Convert journal entries to social posts
  const convertJournalToPosts = (conversationsData: any): SocialPost[] => {
    const socialPosts: SocialPost[] = [];
    
    console.log('🔄 Converting conversations data:', conversationsData);
    
    // Handle the actual API response structure: {conversations: {date: [entries]}}
    if (conversationsData && conversationsData.conversations) {
      const conversations = conversationsData.conversations;
      console.log('📅 Processing conversations:', conversations);
      
      // Iterate through each date's conversations
      Object.keys(conversations).forEach(date => {
        const dailyConversations = conversations[date];
        console.log(`📝 Processing ${date}:`, dailyConversations);
        
        if (Array.isArray(dailyConversations)) {
          dailyConversations.forEach((entry, index) => {
            console.log(`📄 Creating post from entry ${index}:`, entry);
            // Create a post from each conversation entry
            const post: SocialPost = {
              id: `${entry.session_id}-${date}-${index}`,
              user: {
                name: 'Travel Journal',
                username: 'journal',
                avatar: undefined,
              },
              content: `${entry.message}\n\n${entry.response}`,
              image: entry.photo_url,
              timestamp: entry.timestamp,
              likes: Math.floor(Math.random() * 20), // Random likes for demo
              comments: Math.floor(Math.random() * 5),
              isLiked: false,
              location: entry.location_name,
            };
            socialPosts.push(post);
          });
        }
      });
    }
    
    console.log(`✅ Created ${socialPosts.length} social posts`);
    
    // Sort by timestamp (newest first)
    return socialPosts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  };

  const loadJournalData = async () => {
    try {
      console.log('📱 Loading journal data for social feed...');
      
      // Check if user is authenticated with Firebase
      const currentUser = auth.currentUser;
      if (!currentUser) {
        console.log('❌ No authenticated user found');
        throw new Error('User not authenticated');
      }
      
      console.log('✅ User authenticated:', currentUser.uid);
      
      // Get Firebase ID token for API calls
      const token = await currentUser.getIdToken();
      console.log('🔑 Firebase token obtained');
      
      // Try to get user's conversations using the authenticated API
      const conversationsResponse = await apiClient.get('/journal/conversations');
      console.log('💬 Journal conversations:', conversationsResponse.data);
      
      if (conversationsResponse.data && conversationsResponse.data.conversations) {
        const journalPosts = convertJournalToPosts(conversationsResponse.data);
        setPosts(journalPosts);
        console.log(`📝 Converted ${journalPosts.length} journal entries to social posts`);
      } else {
        // If no conversations, create a test conversation
        console.log('📝 No conversations found, creating test conversation...');
        try {
          const testResponse = await apiClient.post('/journal/debug/test-conversation');
          console.log('✅ Test conversation created:', testResponse.data);
          
          // Reload conversations after creating test data
          const newConversationsResponse = await apiClient.get('/journal/conversations');
          if (newConversationsResponse.data && newConversationsResponse.data.conversations) {
            const journalPosts = convertJournalToPosts(newConversationsResponse.data);
            setPosts(journalPosts);
            console.log(`📝 Converted ${journalPosts.length} journal entries to social posts`);
          }
        } catch (testError) {
          console.error('❌ Error creating test conversation:', testError);
        }
      }
    } catch (error) {
      console.error('❌ Error loading journal data:', error);
      
      // Check if it's an authentication error
      if (error instanceof Error && error.message === 'User not authenticated') {
        console.log('🔐 User not authenticated, showing login prompt');
        setPosts([]); // Show empty state
      } else {
        // Set some demo posts if API fails for other reasons
        console.log('📱 Showing demo posts as fallback');
        setPosts([
          {
            id: 'demo-1',
            user: {
              name: 'Travel Journal',
              username: 'journal',
            },
            content: 'Just had an amazing conversation with the locals! They told me about the best hidden spots in the city.',
            timestamp: new Date().toISOString(),
            likes: 12,
            comments: 3,
            isLiked: false,
            location: 'Paris, France',
          },
          {
            id: 'demo-2',
            user: {
              name: 'Travel Journal',
              username: 'journal',
            },
            content: 'Discovered this incredible restaurant today. The food was absolutely amazing!',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            likes: 8,
            comments: 1,
            isLiked: true,
            location: 'Tokyo, Japan',
          },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJournalData();
  }, []);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadJournalData();
    setRefreshing(false);
  }, []);

  const handleLike = (postId: string) => {
    setPosts(prevPosts =>
      prevPosts.map(post =>
        post.id === postId
          ? {
              ...post,
              isLiked: !post.isLiked,
              likes: post.isLiked ? post.likes - 1 : post.likes + 1,
            }
          : post
      )
    );
  };

  const handleComment = (postId: string) => {
    console.log('Comment on post:', postId);
    // TODO: Implement comment functionality
  };

  const handleShare = (postId: string) => {
    console.log('Share post:', postId);
    // TODO: Implement share functionality
  };

  const handleCreatePost = async (content: string, image?: string) => {
    const newPost: SocialPost = {
      id: `new-${Date.now()}`,
      user: {
        name: 'You',
        username: 'you',
      },
      content,
      image,
      timestamp: new Date().toISOString(),
      likes: 0,
      comments: 0,
      isLiked: false,
    };
    
    setPosts(prevPosts => [newPost, ...prevPosts]);
    setShowPostForm(false);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading your travel stories...</Text>
      </View>
    );
  }

  // Check if user is not authenticated
  if (!auth.currentUser && posts.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Please log in to view your travel stories</Text>
        <Text style={styles.subText}>Your journal conversations will appear here once you're authenticated</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Travel Stories</Text>
        <Text style={styles.headerSubtitle}>Share your journey with the world</Text>
      </View>
      
      <PostList
        posts={posts}
        onLike={handleLike}
        onComment={handleComment}
        onShare={handleShare}
        onRefresh={handleRefresh}
        refreshing={refreshing}
      />
      
      {showPostForm && (
        <PostForm
          onSubmit={handleCreatePost}
          onCancel={() => setShowPostForm(false)}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F9FA',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F8F9FA',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#8E8E93',
  },
  subText: {
    marginTop: 8,
    fontSize: 14,
    color: '#8E8E93',
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  header: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 16,
    paddingVertical: 20,
    paddingTop: 60, // Account for status bar
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#8E8E93',
    marginTop: 4,
  },
});