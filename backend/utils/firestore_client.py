import firebase_admin
from firebase_admin import credentials, firestore, auth
from config.settings import settings
import json
import os

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        # Check if firebase-key.json exists
        if os.path.exists("firebase-key.json"):
            cred = credentials.Certificate("firebase-key.json")
        else:
            # Use environment variables to create credentials
            firebase_config = {
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "private_key_id": settings.firebase_private_key_id,
                "private_key": settings.firebase_private_key.replace('\\n', '\n'),
                "client_email": settings.firebase_client_email,
                "client_id": settings.firebase_client_id,
                "auth_uri": settings.firebase_auth_uri,
                "token_uri": settings.firebase_token_uri,
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.firebase_client_email}"
            }
            cred = credentials.Certificate(firebase_config)
        
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

# Initialize Firestore client
db = initialize_firebase()
