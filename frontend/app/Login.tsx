// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
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
const analytics = getAnalytics(app);