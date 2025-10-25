# models/journal_model.py
from pydantic import BaseModel

class JournalEntryRequest(BaseModel):
    photo_url: str
    summary: str
