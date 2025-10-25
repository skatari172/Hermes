import React from 'react';
import { View, StyleSheet, ScrollView, StatusBar } from 'react-native';
import { ProfileHeader, UserProfileSection, MenuSection, LogoutButton } from '../components/profilecomponents';

export default function ProfileScreen() {
  const accountSettingsItems = [
    'Personal information',
    'Notifications',
    'Time spent',
    'Following'
  ];

  const helpSupportItems = [
    'Privacy policy',
    'Terms & Conditions',
    'FAQ & Help'
  ];

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />
      
      <ProfileHeader />

      <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
        <UserProfileSection />
        
        <MenuSection title="Account settings" items={accountSettingsItems} />
        
        <MenuSection title="Help & Support" items={helpSupportItems} />
        
        <LogoutButton />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  scrollContainer: {
    flex: 1,
    paddingHorizontal: 20,
  },
});