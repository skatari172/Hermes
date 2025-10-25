"""
Conversation summarizer for maintaining running summaries of chat sessions.
Updates conversation summaries as new messages are added.
"""

from typing import Dict, Optional, Any
from datetime import datetime
import asyncio
from config.logger import get_logger

logger = get_logger(__name__)

class ConversationSummarizer:
    """Maintains running summaries of conversation sessions."""
    
    def __init__(self):
        # Structure: {user_id: {session_id: summary}}
        self._summaries: Dict[str, Dict[str, str]] = {}
        self._lock = asyncio.Lock()
    
    async def update_summary(self, user_id: str, session_id: str, conversation_turn: Dict[str, Any]):
        """
        Update conversation summary with new turn.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            conversation_turn: New conversation turn data
        """
        async with self._lock:
            if user_id not in self._summaries:
                self._summaries[user_id] = {}
            
            if session_id not in self._summaries[user_id]:
                self._summaries[user_id][session_id] = ""
            
            # Simple summarization logic (in a real implementation, you'd use an LLM)
            user_message = conversation_turn.get("user_message", "")
            hermes_response = conversation_turn.get("hermes_response", "")
            
            # Extract key topics from the conversation
            current_summary = self._summaries[user_id][session_id]
            
            # Simple keyword extraction and summary building
            new_summary_parts = []
            if user_message:
                new_summary_parts.append(f"User asked about: {user_message[:100]}...")
            if hermes_response:
                new_summary_parts.append(f"Hermes responded about: {hermes_response[:100]}...")
            
            if new_summary_parts:
                new_summary = " | ".join(new_summary_parts)
                if current_summary:
                    self._summaries[user_id][session_id] = f"{current_summary} | {new_summary}"
                else:
                    self._summaries[user_id][session_id] = new_summary
                
                # Keep summary length reasonable
                if len(self._summaries[user_id][session_id]) > 1000:
                    self._summaries[user_id][session_id] = self._summaries[user_id][session_id][-1000:]
            
            logger.debug(f"Updated summary for session {session_id} of user {user_id}")
    
    async def get_summary(self, user_id: str, session_id: str) -> str:
        """
        Get conversation summary for a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Conversation summary
        """
        async with self._lock:
            if user_id not in self._summaries or session_id not in self._summaries[user_id]:
                return "No conversation summary available yet."
            
            return self._summaries[user_id][session_id]
    
    async def clear_summary(self, user_id: str, session_id: str):
        """
        Clear conversation summary for a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        async with self._lock:
            if user_id in self._summaries and session_id in self._summaries[user_id]:
                del self._summaries[user_id][session_id]
                logger.info(f"Cleared summary for session {session_id} of user {user_id}")
    
    async def get_all_summaries(self, user_id: str) -> Dict[str, str]:
        """
        Get all summaries for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of session_id to summary
        """
        async with self._lock:
            if user_id not in self._summaries:
                return {}
            return self._summaries[user_id].copy()

# Global conversation summarizer instance
conversation_summarizer = ConversationSummarizer()
