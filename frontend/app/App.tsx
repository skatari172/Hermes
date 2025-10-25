import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import BottomTabsNavigator from './navigation/BottomTabsNavigator';

export default function App() {
  return (
    <NavigationContainer>
      <BottomTabsNavigator />
    </NavigationContainer>
  );
}