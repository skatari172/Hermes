import React, { useState } from 'react';
import Login from '../Login';
import Register from '../Register';

export default function AuthNavigator() {
  const [currentScreen, setCurrentScreen] = useState<'Login' | 'Register'>('Login');

  const navigateToRegister = () => setCurrentScreen('Register');
  const navigateToLogin = () => setCurrentScreen('Login');

  if (currentScreen === 'Register') {
    return <Register onNavigateToLogin={navigateToLogin} />;
  }

  return <Login onNavigateToRegister={navigateToRegister} />;
}
