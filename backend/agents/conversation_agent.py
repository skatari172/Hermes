"""
Conversation Agent for Hermes AI Cultural Companion.
Handles dialogue with scene and knowledge context integration.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from utils.gemini_client import gemini_client
from utils.bus import EventBus
from memory.session_store import session_store
from memory.summarizer import conversation_summarizer
from config.logger import get_logger

logger = get_logger(__name__)

class ConversationAgent:
    """Handles dialogue with integrated scene and knowledge context."""
    
    def __init__(self):
        self.bus = EventBus()
        self.session_store = session_store
        self.summarizer = conversation_summarizer
        
        # Register for relevant events
        self.bus.subscribe("scene_analyzed", self._handle_scene_analysis)
        self.bus.subscribe("geo_context_ready", self._handle_geo_context)
        
        # Context storage
        self.current_scene_context: Optional[Dict] = None
        self.current_geo_context: Optional[Dict] = None
        self.conversation_history: List[Dict] = []
    
    async def _handle_scene_analysis(self, event_data: Dict):
        """Handle scene analysis results from PerceptionAgent."""
        self.current_scene_context = event_data
        logger.info(f"Scene context updated: {event_data.get('summary', 'No summary')}")
    
    async def _handle_geo_context(self, event_data: Dict):
        """Handle geographic context from GeoAgent."""
        self.current_geo_context = event_data
        logger.info(f"Geo context updated: {event_data.get('location', 'Unknown location')}")
    
    def _build_context_prompt(self, user_message: str) -> str:
        """Build comprehensive context prompt for LLM."""
        context_parts = []
        
        # Add scene context if available
        if self.current_scene_context:
            scene_info = self.current_scene_context.get('analysis', {})
            context_parts.append(f"**Current Scene Analysis:**")
            context_parts.append(f"- What I see: {scene_info.get('description', 'No description available')}")
            context_parts.append(f"- Cultural elements: {scene_info.get('cultural_elements', 'None identified')}")
            context_parts.append(f"- Text/OCR: {scene_info.get('text_content', 'No text detected')}")
            context_parts.append("")
        
        # Add geographic context if available
        if self.current_geo_context:
            geo_info = self.current_geo_context
            context_parts.append(f"**Location Context:**")
            context_parts.append(f"- Current location: {geo_info.get('formatted_address', 'Unknown')}")
            context_parts.append(f"- Nearby places: {', '.join(geo_info.get('nearby_places', [])[:3])}")
            context_parts.append(f"- Cultural significance: {geo_info.get('cultural_significance', 'Not specified')}")
            context_parts.append("")
        
        # Add conversation history
        if self.conversation_history:
            context_parts.append("**Recent Conversation:**")
            for msg in self.conversation_history[-3:]:  # Last 3 messages
                role = "User" if msg['role'] == 'user' else "Hermes"
                context_parts.append(f"- {role}: {msg['content']}")
            context_parts.append("")
        
        # Add user's current message
        context_parts.append(f"**User's Current Message:** {user_message}")
        context_parts.append("")
        
        # Add instructions
        context_parts.append("**Instructions:**")
        context_parts.append("You are Hermes, an AI cultural companion helping travelers understand and document their experiences.")
        context_parts.append("Provide helpful, engaging responses that combine the visual scene, location context, and conversation history.")
        context_parts.append("Be conversational, informative, and culturally sensitive.")
        context_parts.append("If the user asks about something not visible in the scene, acknowledge this and provide general helpful information.")
        
        return "\n".join(context_parts)
    
    async def process_message(
        self, 
        user_message: str, 
        user_id: str, 
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process user message with full context integration.
        
        Args:
            user_message: User's text or transcribed speech
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Response with text and metadata
        """
        try:
            # Get or create session
            session = await self.session_store.get_session(user_id, session_id)
            
            # Build context-aware prompt
            context_prompt = self._build_context_prompt(user_message)
            
            # Generate response using Gemini
            response = await gemini_client.generate_text(
                prompt=context_prompt,
                model="gemini-1.5-flash",
                max_tokens=500,
                temperature=0.7
            )
            
            # Store conversation turn
            conversation_turn = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_message": user_message,
                "hermes_response": response,
                "scene_context": self.current_scene_context,
                "geo_context": self.current_geo_context
            }
            
            # Update session
            await self.session_store.add_message(user_id, session_id, {
                "role": "user",
                "content": user_message,
                "timestamp": conversation_turn["timestamp"]
            })
            
            await self.session_store.add_message(user_id, session_id, {
                "role": "assistant", 
                "content": response,
                "timestamp": conversation_turn["timestamp"]
            })
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": conversation_turn["timestamp"]
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": conversation_turn["timestamp"]
            })
            
            # Keep only last 10 messages in memory
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            # Update conversation summary
            await self.summarizer.update_summary(user_id, session_id, conversation_turn)
            
            # Emit conversation event
            await self.bus.emit("conversation_updated", {
                "user_id": user_id,
                "session_id": session_id,
                "response": response,
                "context": {
                    "scene": self.current_scene_context,
                    "geo": self.current_geo_context
                }
            })
            
            logger.info(f"Processed message for user {user_id}: {response[:100]}...")
            
            return {
                "response": response,
                "context_used": {
                    "scene_available": self.current_scene_context is not None,
                    "geo_available": self.current_geo_context is not None,
                    "conversation_length": len(self.conversation_history)
                },
                "timestamp": conversation_turn["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": "I apologize, but I'm having trouble processing your message right now. Please try again.",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def clear_context(self):
        """Clear current scene and geo context."""
        self.current_scene_context = None
        self.current_geo_context = None
        logger.info("Context cleared")
    
    async def get_conversation_summary(self, user_id: str, session_id: str) -> str:
        """Get conversation summary for the session."""
        return await self.summarizer.get_summary(user_id, session_id)

# Global instance
conversation_agent = ConversationAgent()
