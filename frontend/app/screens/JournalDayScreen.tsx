import React from 'react';
import { View, Text, ScrollView, Image, StyleSheet, Dimensions } from 'react-native';
import { RouteProp, useRoute } from '@react-navigation/native';

type ParamList = {
  JournalDay: {
    date: string;
    diarySummary?: string;
    images?: string[];
    conversations?: any[];
  };
};

export default function JournalDayScreen() {
  const route = useRoute<RouteProp<ParamList, 'JournalDay'>>();
  const { date, diarySummary = '', images = [], conversations = [] } = route.params || {};

  const formattedDate = new Date(date).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <View style={{ flex: 1, backgroundColor: '#fff' }}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.dateHeading}>{formattedDate}</Text>

        <Text style={styles.sectionLabel}>Daily Summary</Text>
        <Text style={styles.summaryText}>{diarySummary || 'No summary available for this day.'}</Text>

        {images && images.length > 0 && (
          <>
            <Text style={[styles.sectionLabel, { marginTop: 20 }]}>Photos</Text>
            <View style={styles.imageGrid}>
              {images.map((uri, idx) => (
                <Image key={idx} source={{ uri }} style={styles.photo} resizeMode="cover" />
              ))}
            </View>
          </>
        )}

        {conversations && conversations.length > 0 && (
          <>
            <Text style={[styles.sectionLabel, { marginTop: 20 }]}>All Entries</Text>
            {conversations.map((c, i) => (
              <View key={i} style={styles.entryCard}>
                <Text style={styles.entryTitle}>{c.message || 'Entry'}</Text>
                <Text style={styles.entryBody}>{c.response || c.diary || ''}</Text>
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </View>
  );
}

const { width } = Dimensions.get('window');
const PHOTO_SIZE = Math.max(100, Math.floor((width - 48) / 3));

const styles = StyleSheet.create({
  container: {
    padding: 16,
    paddingBottom: 40,
  },
  dateHeading: {
    fontSize: 22,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  sectionLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 8,
  },
  summaryText: {
    fontSize: 15,
    color: '#333',
    lineHeight: 22,
  },
  imageGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  photo: {
    width: PHOTO_SIZE,
    height: PHOTO_SIZE,
    borderRadius: 8,
    marginRight: 8,
    marginBottom: 8,
    backgroundColor: '#e9ecef',
  },
  entryCard: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e9ecef',
  },
  entryTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 6,
  },
  entryBody: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
});
