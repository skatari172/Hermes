# backend/routes/journal_routes.py
from fastapi import APIRouter, Depends
from datetime import datetime
from utils.auth_util import verify_firebase_token
from services.db_service import save_journal_entry, get_journal_entries
from models.journal import JournalEntryRequest

router = APIRouter(prefix="/journal", tags=["Journal"])

@router.post("/add")
@router.post("/add")
def add_journal(
    entry: JournalEntryRequest,
    uid: str = Depends(verify_firebase_token)
):
    data = {
        "photoUrl": entry.photo_url,
        "summary": entry.summary,
        "timestamp": datetime.utcnow().isoformat()
    }

    save_journal_entry(uid, data)
    return {"message": "Journal entry saved successfully"}

@router.get("/history")
def get_user_journal(uid: str = Depends(verify_firebase_token)):
    return get_journal_entries(uid)
