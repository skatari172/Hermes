# backend/services/db_service.py
from services.firebase_client import db
from google.cloud import firestore

def save_journal_entry(uid: str, entry: dict):
    """
    Adds a chat summary (photo + summary + timestamp) to the user's Firestore document.
    """
    doc_ref = db.collection("journal").document(uid)

    # If the doc doesn't exist yet, create it with the first entry
    doc = doc_ref.get()
    if not doc.exists:
        doc_ref.set({"conversation": [entry]})
    else:
        # Append entry to conversation array
        doc_ref.update({
            "conversation": firestore.ArrayUnion([entry])
        })


def get_journal_entries(uid: str):
    """
    Retrieves all conversation summaries for a user.
    """
    doc_ref = db.collection("journal").document(uid)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else {"conversation": []}
