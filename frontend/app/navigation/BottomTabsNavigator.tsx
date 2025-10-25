import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { Platform } from 'react-native';
import HomeScreen from '../screens/HomeScreen';
import JournalScreen from '../screens/JournalScreen';
import SocialFeed from '../screens/SocialFeed';
import ProfileScreen from '../screens/ProfileScreen';

const Tab = createBottomTabNavigator();

export default function BottomTabsNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap;

          if (route.name === 'Journal') {
            iconName = focused ? 'book' : 'book-outline';
          } else if (route.name === 'Home') {
            iconName = focused ? 'camera' : 'camera-outline';
          } else if (route.name === 'SocialFeed') {
            iconName = focused ? 'people' : 'people-outline';
          } else if (route.name === 'Profile') {
            iconName = focused ? 'person' : 'person-outline';
          } else {
            iconName = 'help-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#01AFD1',
        tabBarInactiveTintColor: '#043263',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopWidth: 1,
          borderTopColor: '#043263',
          paddingBottom: Platform.OS === 'ios' ? 20 : 5,
          paddingTop: 5,
          height: Platform.OS === 'ios' ? 85 : 60,
        },
        tabBarShowLabel: false,
        headerShown: false,
      })}
    >
      <Tab.Screen 
        name="Journal" 
        component={JournalScreen}
      />
      <Tab.Screen 
        name="Home" 
        component={HomeScreen}
        options={{
          tabBarStyle: {
            backgroundColor: '#FFFFFF',
            borderTopWidth: 1,
            borderTopColor: '#043263',
            paddingBottom: Platform.OS === 'ios' ? 20 : 5,
            paddingTop: 5,
            height: Platform.OS === 'ios' ? 85 : 60,
          },
          tabBarIcon: ({ focused, color, size }) => (
            <Ionicons 
              name={focused ? 'camera' : 'camera-outline'} 
              size={size + 4} 
              color={focused ? '#01AFD1' : color} 
            />
          ),
          tabBarActiveTintColor: '#01AFD1',
        }}
      />
      <Tab.Screen 
        name="SocialFeed" 
        component={SocialFeed}
      />
      <Tab.Screen 
        name="Profile" 
        component={ProfileScreen}
      />
    </Tab.Navigator>
  );
}