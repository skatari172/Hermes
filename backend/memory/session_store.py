"""
Session store for managing user chat sessions and message history.
Stores per-user in-memory chat history with session management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from config.logger import get_logger

logger = get_logger(__name__)

class SessionStore:
    """In-memory session store for chat history."""
    
    def __init__(self):
        # Structure: {user_id: {session_id: [messages]}}
        self._sessions: Dict[str, Dict[str, List[Dict]]] = {}
        self._lock = asyncio.Lock()
    
    async def get_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Get or create a session for a user.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Session data
        """
        async with self._lock:
            if user_id not in self._sessions:
                self._sessions[user_id] = {}
            
            if session_id not in self._sessions[user_id]:
                self._sessions[user_id][session_id] = []
                logger.info(f"Created new session {session_id} for user {user_id}")
            
            return {
                "user_id": user_id,
                "session_id": session_id,
                "messages": self._sessions[user_id][session_id],
                "created_at": datetime.utcnow().isoformat()
            }
    
    async def add_message(self, user_id: str, session_id: str, message: Dict[str, Any]):
        """
        Add a message to a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message: Message data
        """
        async with self._lock:
            if user_id not in self._sessions:
                self._sessions[user_id] = {}
            
            if session_id not in self._sessions[user_id]:
                self._sessions[user_id][session_id] = []
            
            self._sessions[user_id][session_id].append(message)
            logger.debug(f"Added message to session {session_id} for user {user_id}")
    
    async def get_messages(self, user_id: str, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get messages from a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            limit: Optional limit on number of messages
            
        Returns:
            List of messages
        """
        async with self._lock:
            if user_id not in self._sessions or session_id not in self._sessions[user_id]:
                return []
            
            messages = self._sessions[user_id][session_id]
            if limit:
                return messages[-limit:]
            return messages
    
    async def clear_session(self, user_id: str, session_id: str):
        """
        Clear all messages from a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        async with self._lock:
            if user_id in self._sessions and session_id in self._sessions[user_id]:
                self._sessions[user_id][session_id] = []
                logger.info(f"Cleared session {session_id} for user {user_id}")
    
    async def delete_session(self, user_id: str, session_id: str):
        """
        Delete a session entirely.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        async with self._lock:
            if user_id in self._sessions and session_id in self._sessions[user_id]:
                del self._sessions[user_id][session_id]
                logger.info(f"Deleted session {session_id} for user {user_id}")
    
    async def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all session IDs for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of session IDs
        """
        async with self._lock:
            if user_id not in self._sessions:
                return []
            return list(self._sessions[user_id].keys())
    
    async def get_session_count(self, user_id: str) -> int:
        """Get number of sessions for a user."""
        async with self._lock:
            if user_id not in self._sessions:
                return 0
            return len(self._sessions[user_id])

# Global session store instance
session_store = SessionStore()
