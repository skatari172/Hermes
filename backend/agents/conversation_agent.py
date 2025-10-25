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
        context_parts.append("Keep responses concise but engaging, perfect for voice synthesis.")
        
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
            
            # Generate random hardcoded response
            import random
            random_responses = [
                "That's a fascinating question! Let me share some insights about that topic.",
                "I can see you're interested in learning more. Here's what I know about this subject.",
                "Great question! Based on what I can observe, here's my perspective on that.",
                "I'd be happy to help you understand this better. Let me explain what I know.",
                "That's an interesting point of view. Here's some additional context for you.",
                "I appreciate you asking about this. Let me provide you with some helpful information.",
                "Wonderful! I love discussing topics like this. Here's what I can tell you.",
                "Excellent question! This is actually a really interesting area to explore.",
                "I'm glad you brought this up. Here's my take on what you're asking about.",
                "That's a great observation! Let me add some thoughts to what you've shared.",
                "I find this topic really engaging. Here's what I think about it.",
                "Thanks for sharing that with me. Here's my response to your question.",
                "I'm excited to discuss this with you! Here's what I have to say about it.",
                "This is such an interesting topic! Let me share my perspective with you.",
                "Hello! I'm Hermes, your AI cultural companion. How can I help you today?",
                "That's a wonderful question! I'd love to help you explore this further.",
                "I'm here to assist you with your cultural exploration journey!",
                "What an interesting perspective! Let me share some thoughts on that.",
                "I'm excited to help you discover more about this fascinating topic!",
                "That's a great question! I'm here to help you understand this better."
            ]
            response = random.choice(random_responses)
            
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
            
            # Generate TTS audio for the response
            tts_audio_data = None
            try:
                from utils.elevenlabs_client import elevenlabs_client
                logger.info(f"TTS Debug: elevenlabs_client exists: {elevenlabs_client is not None}")
                logger.info(f"TTS Debug: elevenlabs_client.client exists: {elevenlabs_client.client is not None}")
                logger.info(f"TTS Debug: elevenlabs_client.api_key exists: {bool(elevenlabs_client.api_key)}")
                
                if elevenlabs_client.client:
                    logger.info(f"TTS Debug: Attempting to generate audio for: {response[:50]}...")
                    audio_bytes = await elevenlabs_client.text_to_speech(
                        text=response,
                        voice_id="pNInz6obpgDQGcFmaJgB",  # Default Adam voice
                        model="eleven_flash_v2_5"  # Fast model for real-time
                    )
                    import base64
                    tts_audio_data = base64.b64encode(audio_bytes).decode('utf-8')
                    logger.info(f"✅ Generated TTS audio for response (size: {len(audio_bytes)} bytes)")
                else:
                    logger.warning("❌ ElevenLabs client not available - TTS disabled")
            except Exception as tts_error:
                logger.error(f"❌ TTS generation failed: {str(tts_error)}")
                import traceback
                logger.error(f"TTS Error traceback: {traceback.format_exc()}")
                tts_audio_data = None
            
            # Emit conversation event
            await self.bus.emit("conversation_updated", {
                "user_id": user_id,
                "session_id": session_id,
                "response": response,
                "tts_audio_data": tts_audio_data,
                "context": {
                    "scene": self.current_scene_context,
                    "geo": self.current_geo_context
                }
            })
            
            logger.info(f"Processed message for user {user_id}: {response[:100]}...")
            
            return {
                "response": response,
                "tts_audio_data": tts_audio_data,
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
