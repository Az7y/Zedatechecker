// Copy this file to firebase-config.js and fill in your own Firebase project's values.
// Firebase console > Project settings > Your apps > Web app.
// None of these are secret; access is controlled by firestore.rules.
export const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

// The owner login, used for first-time setup and as a backup admin.
// Must match the email in the isOwner() check in firestore.rules.
export const OWNER_EMAIL = "owner@example.com";

// Where "Suggest an improvement" goes. Email for the mailto link; endpoint optional (e.g. a free Formspree URL) to also auto-email.
export const FEEDBACK_EMAIL = "you@example.com";
export const FEEDBACK_ENDPOINT = "";
