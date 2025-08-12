""
NPC Manager for VRChat MCP.

This module handles intelligent NPC behaviors, including conversation management,
state tracking, and integration with language models for dynamic interactions.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from ..models import NPCConversationRequest, SuccessResponse, ErrorResponse

logger = logging.getLogger(__name__)

class NPCManager:
    """
    Manages NPC behaviors and conversations in VRChat.
    
    Handles conversation state, integrates with language models for responses,
    and manages NPC animations/expressions during interactions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the NPC manager with configuration."""
        self.config = {
            'default_model': config.get('default_model', 'gpt-4'),
            'max_history': config.get('max_history', 10),
            'response_timeout': config.get('response_timeout', 30.0),
            'enable_emotions': config.get('enable_emotions', True)
        }
        
        # Track NPC states and conversations
        self.npcs: Dict[str, Dict[str, Any]] = {}
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
        
        # Initialize language model integration
        self._init_language_model()
    
    def _init_language_model(self) -> None:
        """Initialize the language model for NPC responses."""
        # This would be replaced with actual model initialization
        self.language_model = {
            'model': self.config['default_model'],
            'temperature': 0.7,
            'max_tokens': 150
        }
        
        logger.info(
            "Initialized language model",
            extra={"model": self.config['default_model']}
        )
    
    async def start_conversation(
        self,
        npc_id: str,
        user_id: str,
        initial_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a new conversation with an NPC."""
        conversation_id = f"{npc_id}:{user_id}"
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
            
            # Initialize NPC state if not exists
            if npc_id not in self.npcs:
                self.npcs[npc_id] = {
                    'state': 'idle',
                    'current_conversation': None,
                    'mood': 'neutral',
                    'last_interaction': asyncio.get_event_loop().time()
                }
            
            # Add system prompt as first message
            system_prompt = self._get_system_prompt(npc_id)
            self.conversations[conversation_id].append({
                'role': 'system',
                'content': system_prompt
            })
            
            # Add initial user message if provided
            if initial_message:
                await self.add_message(conversation_id, 'user', initial_message)
            
            self.npcs[npc_id]['current_conversation'] = conversation_id
            self.npcs[npc_id]['state'] = 'in_conversation'
            
            logger.info(
                "Started new conversation",
                extra={"npc_id": npc_id, "user_id": user_id}
            )
            
            return {
                'status': 'success',
                'conversation_id': conversation_id,
                'npc_id': npc_id,
                'message': 'Conversation started'
            }
        
        return {
            'status': 'error',
            'error': 'Conversation already exists',
            'conversation_id': conversation_id
        }
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> Dict[str, Any]:
        """Add a message to an existing conversation."""
        if conversation_id not in self.conversations:
            return {
                'status': 'error',
                'error': 'Conversation not found',
                'conversation_id': conversation_id
            }
        
        # Add the message to the conversation history
        self.conversations[conversation_id].append({
            'role': role,
            'content': content,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        # Trim history if needed
        if len(self.conversations[conversation_id]) > self.config['max_history'] * 2 + 1:  # *2 for user/assistant pairs, +1 for system
            self.conversations[conversation_id] = [
                self.conversations[conversation_id][0]  # Keep system prompt
            ] + self.conversations[conversation_id][-self.config['max_history']*2:]
        
        logger.debug(
            "Added message to conversation",
            extra={
                "conversation_id": conversation_id,
                "role": role,
                "content_length": len(content)
            }
        )
        
        return {'status': 'success'}
    
    async def get_response(
        self,
        conversation_id: str,
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a response from the NPC in the specified conversation."""
        if conversation_id not in self.conversations:
            return {
                'status': 'error',
                'error': 'Conversation not found',
                'conversation_id': conversation_id
            }
        
        # Add user message if provided
        if user_message:
            await self.add_message(conversation_id, 'user', user_message)
        
        # Get conversation history
        messages = self.conversations[conversation_id]
        
        try:
            # Generate response using language model
            # In a real implementation, this would call an actual language model API
            response = await self._generate_response(messages)
            
            # Add assistant's response to conversation
            await self.add_message(conversation_id, 'assistant', response)
            
            # Update NPC state based on response
            npc_id = conversation_id.split(':', 1)[0]
            if npc_id in self.npcs:
                self.npcs[npc_id]['last_interaction'] = asyncio.get_event_loop().time()
            
            return {
                'status': 'success',
                'response': response,
                'conversation_id': conversation_id
            }
            
        except Exception as e:
            logger.error("Failed to generate NPC response", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'conversation_id': conversation_id
            }
    
    async def _generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response using the language model."""
        # This is a placeholder that would be replaced with actual model calls
        # In a real implementation, this would call an API like OpenAI's GPT
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Simple echo response for demonstration
        last_user_message = next(
            (msg['content'] for msg in reversed(messages) if msg['role'] == 'user'),
            "Hello! How can I help you today?"
        )
        
        return f"I understand you said: {last_user_message}"
    
    async def end_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """End an NPC conversation and clean up resources."""
        if conversation_id in self.conversations:
            # Update NPC state
            npc_id = conversation_id.split(':', 1)[0]
            if npc_id in self.npcs:
                self.npcs[npc_id]['state'] = 'idle'
                self.npcs[npc_id]['current_conversation'] = None
            
            # Remove conversation
            del self.conversations[conversation_id]
            
            logger.info("Ended conversation", extra={"conversation_id": conversation_id})
            
            return {
                'status': 'success',
                'message': 'Conversation ended',
                'conversation_id': conversation_id
            }
        
        return {
            'status': 'error',
            'error': 'Conversation not found',
            'conversation_id': conversation_id
        }
    
    def _get_system_prompt(self, npc_id: str) -> str:
        """Generate a system prompt for the NPC."""
        # This would be customized based on NPC personality and role
        return (
            "You are a helpful NPC in VRChat. "
            "Respond to users in a friendly and engaging manner. "
            "Keep responses concise and appropriate for a virtual environment. "
            "You can express emotions through text and suggested animations."
        )
    
    # Helper methods for NPC state management
    def get_npc_state(self, npc_id: str) -> Dict[str, Any]:
        """Get the current state of an NPC."""
        return self.npcs.get(npc_id, {'state': 'not_found'})
    
    def update_npc_state(
        self,
        npc_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update the state of an NPC."""
        if npc_id not in self.npcs:
            self.npcs[npc_id] = {
                'state': 'idle',
                'current_conversation': None,
                'mood': 'neutral',
                'last_interaction': asyncio.get_event_loop().time()
            }
        
        self.npcs[npc_id].update(updates)
        return self.npcs[npc_id]
