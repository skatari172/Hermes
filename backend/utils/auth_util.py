from fastapi import HTTPException, Header
from services.firebase_client import initialize_firebase  # Ensure Firebase is initialized
from firebase_admin import auth

def verify_firebase_token(authorization: str = Header(...)):
    """
    Expect header: Authorization: Bearer <Firebase_ID_Token>
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header format")

    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]
        return uid
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Expired ID token") 
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
