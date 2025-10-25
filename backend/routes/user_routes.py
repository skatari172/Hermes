# routes/user_routes.py
from fastapi import APIRouter, Depends, HTTPException
from utils.firebase_client import initialize_firebase  # Ensure Firebase is initialized
from utils.auth_util import verify_firebase_token
from firebase_admin import auth
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/user", tags=["User"])

class UserProfile(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None
    uid: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    uid: Optional[str] = None
    display_name: Optional[str] = None

@router.post("/register", response_model=AuthResponse)
def register_user(user_data: RegisterRequest):
    """Register a new user with Firebase Auth"""
    try:
        # Create user in Firebase Auth
        user_record = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=f"{user_data.first_name} {user_data.last_name}"
        )
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            uid=user_record.uid,
            display_name=f"{user_data.first_name} {user_data.last_name}"
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Email already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=AuthResponse)
def login_user(login_data: LoginRequest):
    """Login user using Firebase Auth"""
    try:
        # Get user by email from Firebase Auth
        user_record = auth.get_user_by_email(login_data.email)
        
        # Note: Firebase Admin SDK doesn't have password verification
        # In production, you'd use Firebase client SDK for authentication
        # For now, we'll just return success if user exists
        return AuthResponse(
            success=True,
            message="Login successful",
            uid=user_record.uid,
            display_name=user_record.display_name
        )
    except auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.get("/profile")
def get_user_profile(uid: str = Depends(verify_firebase_token)):
    """Get user profile data from Firebase Auth"""
    try:
        user_record = auth.get_user(uid)
        
        return {
            "uid": uid, 
            "profile": {
                "email": user_record.email,
                "display_name": user_record.display_name,
                "photo_url": user_record.photo_url,
                "email_verified": user_record.email_verified,
                "created_at": user_record.user_metadata.creation_timestamp,
                "last_sign_in": user_record.user_metadata.last_sign_in_timestamp
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")

@router.put("/profile")
def update_user_profile(
    profile_data: UpdateProfileRequest,
    uid: str = Depends(verify_firebase_token)
):
    """Update user profile in Firebase Auth"""
    try:
        update_data = {}
        
        if profile_data.display_name is not None:
            update_data['display_name'] = profile_data.display_name
        
        auth.update_user(uid, **update_data)
        return {"message": "Profile updated successfully", "uid": uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

@router.delete("/profile")
def delete_user_profile(uid: str = Depends(verify_firebase_token)):
    """Delete user from Firebase Auth"""
    try:
        auth.delete_user(uid)
        return {"message": "User deleted successfully", "uid": uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")
