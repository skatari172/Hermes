import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function JournalScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Journal Screen</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#E5ECFF',
  },
  text: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#043263',
  },
});