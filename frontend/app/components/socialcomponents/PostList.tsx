import React from 'react';
import { FlatList, StyleSheet, RefreshControl } from 'react-native';
import PostCard from './PostCard';

interface PostListProps {
  posts: Array<{
    id: string;
    user: {
      name: string;
      username: string;
      avatar?: string;
    };
    content: string;
    image?: string;
    timestamp: string;
    likes: number;
    comments: number;
    isLiked: boolean;
    location?: string;
  }>;
  onLike: (postId: string) => void;
  onComment: (postId: string) => void;
  onShare: (postId: string) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
}

export default function PostList({ 
  posts, 
  onLike, 
  onComment, 
  onShare, 
  onRefresh, 
  refreshing = false 
}: PostListProps) {
  const renderPost = ({ item }: { item: any }) => (
    <PostCard
      post={item}
      onLike={onLike}
      onComment={onComment}
      onShare={onShare}
    />
  );

  return (
    <FlatList
      data={posts}
      renderItem={renderPost}
      keyExtractor={(item) => item.id}
      contentContainerStyle={styles.listContainer}
      refreshControl={
        onRefresh ? (
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={['#007AFF']}
            tintColor="#007AFF"
          />
        ) : undefined
      }
      showsVerticalScrollIndicator={false}
    />
  );
}

const styles = StyleSheet.create({
  listContainer: {
    paddingVertical: 8,
  },
});
