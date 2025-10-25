import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';

export default function LogoutButton() {
  return (
    <TouchableOpacity style={styles.logoutButton}>
      <Text style={styles.logoutText}>Log out</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  logoutButton: {
    paddingVertical: 20,
    alignItems: 'center',
    marginBottom: 30,
  },
  logoutText: {
    fontSize: 16,
    color: '#FF4444',
    fontWeight: '500',
  },
});
