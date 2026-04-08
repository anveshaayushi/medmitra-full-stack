import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyAbqLzGbV7R3eV4pzfiMkHoDJ-XBsfzaKU",
  authDomain: "medmitra-9cfa1.firebaseapp.com",
  projectId: "medmitra-9cfa1",
  storageBucket: "medmitra-9cfa1.firebasestorage.app",
  messagingSenderId: "897996796070",
  appId: "1:897996796070:web:add72764d7c337c8174467",
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const db = getFirestore(app);