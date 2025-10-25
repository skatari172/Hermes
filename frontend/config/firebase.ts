import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getStorage } from 'firebase/storage';
import { getFirestore } from 'firebase/firestore';

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDgC55kPvMxUFSoXwFZQ40n9PZrcLNPfjw",
  authDomain: "hermes-521f9.firebaseapp.com",
  projectId: "hermes-521f9",
  storageBucket: "hermes-521f9.appspot.com",
  messagingSenderId: "927682530223",
  appId: "1:927682530223:web:35a344c42ce000da37bd5a",
  measurementId: "G-RE060Z5H5X"
};

// Initialize Firebase (safe guard against double initialization)
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();

// Initialize Firebase services
export const auth = getAuth(app);
export const storage = getStorage(app);
export const db = getFirestore(app);

export default app;
