import { useState, useEffect } from 'react';
import apiClient from '../api/apiClient';

interface Pin {
  id: string;
  category: string;
  description?: string;
  title?: string;
  latitude: number;
  longitude: number;
  createdAt?: string;
  upVotes?: number;
  downVotes?: number;
}

export const usePins = () => {
  const [pins, setPins] = useState<Pin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPins = async () => {
    try {
      setLoading(true);
      setError(null);
      // TODO: Replace with actual API call when backend is ready
      const fetchedPins: Pin[] = []; // Empty array for now
      setPins(fetchedPins);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load pins';
      setError(errorMessage);
      console.error('Error loading pins:', err);
    } finally {
      setLoading(false);
    }
  };

  const refreshPins = () => {
    loadPins();
  };

  const addPin = (pin: Pin) => {
    setPins(prev => [...prev, pin]);
  };

  const updatePinVotes = (pinId: string, upVotes: number, downVotes: number) => {
    setPins(prev => prev.map(pin => 
      pin.id === pinId 
        ? { ...pin, upVotes, downVotes }
        : pin
    ));
  };

  useEffect(() => {
    loadPins();
  }, []);

  return {
    pins,
    loading,
    error,
    refreshPins,
    addPin,
    updatePinVotes,
    loadPins
  };
};