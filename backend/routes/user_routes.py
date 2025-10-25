# routes/user_routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from services.firebase_client import initialize_firebase  # Ensure Firebase is initialized
from utils.auth_util import verify_firebase_token
from firebase_admin import auth
from pydantic import BaseModel, EmailStr
from typing import Optional
from utils.storage_client import storage_client
from services import db_service
from config.logger import get_logger
from urllib.parse import urlparse, urljoin

logger = get_logger(__name__)


def _normalize_photo_url(photo_url: str, request: Request) -> str:
    """If photo_url points to localhost, rewrite it to use the request base URL so mobile clients can reach it."""
    try:
        if not photo_url:
            return photo_url
        parsed = urlparse(photo_url)
        hostname = parsed.hostname
        if hostname in ("localhost", "127.0.0.1"):
            # Rebuild URL using the incoming request base URL
            base = str(request.base_url)
            # Use the path from the parsed URL
            return urljoin(base, parsed.path.lstrip('/'))
        return photo_url
    except Exception as e:
        logger.debug(f"normalize_photo_url failed: {e}")
        return photo_url

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
def get_user_profile(uid: str = Depends(verify_firebase_token), request: Request = None):
    """Get user profile data from Firebase Auth"""
    try:
        user_record = auth.get_user(uid)
        logger.info(f"GET /user/profile for uid={uid} -> display_name={user_record.display_name} photo={user_record.photo_url}")

        photo = user_record.photo_url
        if request and photo:
            photo = _normalize_photo_url(photo, request)

        return {
            "uid": uid,
            "profile": {
                "email": user_record.email,
                "display_name": user_record.display_name,
                "photo_url": photo,
                "email_verified": user_record.email_verified,
                "created_at": user_record.user_metadata.creation_timestamp,
                "last_sign_in": user_record.user_metadata.last_sign_in_timestamp,
            },
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


@router.post('/profile/photo')
async def upload_profile_photo(request: Request, file: UploadFile = File(...), uid: str = Depends(verify_firebase_token)):
    """Upload or replace the authenticated user's profile photo.

    Stores the file at uploads/profile/{uid}.jpg (overwrites existing).
    Returns the public URL to the uploaded file and updates the user's auth/profile record.
    """
    try:
        # Validate file
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail='Invalid file type; image required')

            data = await file.read()
            if len(data) == 0:
                raise HTTPException(status_code=400, detail='Empty file')

            logger.info(f"POST /user/profile/photo received file='{file.filename}' content_type={file.content_type} size={len(data)} for uid={uid}")

            # Upload via storage client (will use Firebase bucket if configured or local fallback)
            photo_url = await storage_client.upload_profile_image(image_data=data, user_id=uid, content_type=file.content_type)

            logger.info(f"Profile image stored for uid={uid} -> {photo_url}")

            if not photo_url:
                raise HTTPException(status_code=500, detail='Failed to store profile image')

            # Normalize local URLs so clients receive a reachable address
            try:
                photo_url = _normalize_photo_url(photo_url, request)
            except Exception:
                pass

            # Update Firebase Auth user profile (photo_url)
            try:
                auth.update_user(uid, photo_url=photo_url)
            except Exception as e:
                # Log but continue - still return URL
                logger.warning(f"Warning: failed to update Firebase Auth photo_url: {e}")

            # Update Firestore users/{uid} doc with photo_url
            try:
                db_service_ref = db_service
                # Save minimal user metadata
                db_service_ref.save_journal_entry  # touch to ensure import
                from services.firebase_client import db
                db.collection('users').document(uid).set({
                    'photo_url': photo_url
                }, merge=True)
            except Exception as e:
                logger.warning(f"Warning: failed to update Firestore user doc: {e}")

            return {'status': 'success', 'photo_url': photo_url}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
