# routes/user_routes.py
from fastapi import APIRouter, Depends, HTTPException
from utils.auth_util import verify_firebase_token
from utils.firestore_client import db
from firebase_admin import firestore
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/user", tags=["User"])

class UserProfile(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None
    preferences: Optional[dict] = {}

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    preferences: Optional[dict] = None

@router.get("/profile")
def get_user_profile(uid: str = Depends(verify_firebase_token)):
    """Get user profile data from Firestore"""
    try:
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            return {"uid": uid, "profile": user_doc.to_dict()}
        else:
            # Create default profile if it doesn't exist
            default_profile = {
                "created_at": firestore.SERVER_TIMESTAMP,
                "preferences": {}
            }
            user_ref.set(default_profile)
            return {"uid": uid, "profile": default_profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")

@router.put("/profile")
def update_user_profile(
    profile_data: UpdateProfileRequest,
    uid: str = Depends(verify_firebase_token)
):
    """Update user profile in Firestore"""
    try:
        user_ref = db.collection('users').document(uid)
        update_data = {}
        
        if profile_data.display_name is not None:
            update_data['display_name'] = profile_data.display_name
        if profile_data.preferences is not None:
            update_data['preferences'] = profile_data.preferences
        
        update_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        user_ref.update(update_data)
        return {"message": "Profile updated successfully", "uid": uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

@router.delete("/profile")
def delete_user_profile(uid: str = Depends(verify_firebase_token)):
    """Delete user profile from Firestore"""
    try:
        user_ref = db.collection('users').document(uid)
        user_ref.delete()
        return {"message": "Profile deleted successfully", "uid": uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting profile: {str(e)}")
