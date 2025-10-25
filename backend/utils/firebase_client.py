import firebase_admin
from firebase_admin import credentials

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully")
    else:
        print("Firebase already initialized").gitignore

# Initialize Firebase
initialize_firebase()
