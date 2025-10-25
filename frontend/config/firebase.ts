import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDgC55kPvMxUFSoXwFZQ40n9PZrcLNPfjw",
  authDomain: "hermes-521f9.firebaseapp.com",
  projectId: "hermes-521f9",
  storageBucket: "hermes-521f9.firebasestorage.app",
  messagingSenderId: "927682530223",
  appId: "1:927682530223:web:35a344c42ce000da37bd5a",
  measurementId: "G-RE060Z5H5X"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Auth and get a reference to the service
export const auth = getAuth(app);
export default app;
