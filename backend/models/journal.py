# models/journal_model.py
from pydantic import BaseModel
from typing import Optional

class JournalEntryRequest(BaseModel):
    photo_url: str
    summary: str

class JournalEntryUpdate(BaseModel):
    summary: str
    diary: Optional[str] = None

class ConversationEntry(BaseModel):
    message: str
    response: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    photo_url: Optional[str] = None
    session_id: str
