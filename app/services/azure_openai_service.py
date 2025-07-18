"""
Azure OpenAI Service for chat completion with tools
"""
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncAzureOpenAI
from openai import AuthenticationError, RateLimitError, APIConnectionError, APIError
from config.config import config
from config.logger_config import logger
from app.tools.tool_manager import ToolManager


class AzureOpenAIService:
    """Service to interact with Azure OpenAI"""
    
    def __init__(self):
        try:
            # Log configuration details (without exposing API key)
            logger.info(f"Initializing Azure OpenAI with endpoint: {config.AZURE_OPENAI_ENDPOINT}")
            logger.info(f"API Version: {config.AZURE_OPENAI_API_VERSION}")
            logger.info(f"Deployment: {config.AZURE_OPENAI_DEPLOYMENT_NAME}")
            logger.info(f"API Key configured: {bool(config.AZURE_OPENAI_API_KEY)}")
            
            self.client = AsyncAzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_API_KEY,
                api_version=config.AZURE_OPENAI_API_VERSION,
                timeout=30.0,  # Add timeout
                max_retries=3   # Add retries
            )
            self.tool_manager = ToolManager()
            self.system_prompt = """
You are a helpful AI assistant with access to various tools. 
You can help users with:
- General information and questions
- Calculations and data processing  
- API calls and external data retrieval
- Task automation

When a user asks for something that requires using a tool, analyze their request and use the appropriate tool to help them.
Always be helpful, accurate, and provide clear explanations of what you're doing.
"""
            logger.info("Azure OpenAI Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI Service: {str(e)}")
            raise
    
    async def test_connection(self) -> bool:
        """Test the connection to Azure OpenAI"""
        try:
            logger.info("Testing Azure OpenAI connection...")
            
            # Simple test call
            response = await self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            logger.info("Connection test successful")
            return True
            
        except AuthenticationError as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
        except APIConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def chat_completion(
        self, 
        message: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Get chat completion from Azure OpenAI
        
        Args:
            message: User message
            conversation_history: Previous conversation messages
            stream: Whether to stream the response
            
        Returns:
            Response from Azure OpenAI
        """
        try:
            # Test connection first
            if not await self.test_connection():
                raise Exception("Cannot connect to Azure OpenAI service")
            
            # Prepare messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append(msg)
                    else:
                        logger.warning(f"Invalid message format in history: {msg}")
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            logger.info(f"Prepared {len(messages)} messages for completion")
            
            # Get available tools
            tools = self.tool_manager.get_tools_schema()
            logger.info(f"Available tools: {len(tools)}")
            
            # Make API call
            if stream:
                return await self._stream_completion(messages, tools)
            else:
                return await self._regular_completion(messages, tools)
                
        except AuthenticationError as e:
            logger.error(f"Authentication error: {str(e)}")
            raise Exception(f"Authentication failed: Check your API key and endpoint")
        except APIConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            raise Exception(f"Cannot connect to Azure OpenAI: {str(e)}")
        except RateLimitError as e:
            logger.error(f"Rate limit error: {str(e)}")
            raise Exception(f"Rate limit exceeded: {str(e)}")
        except APIError as e:
            logger.error(f"API error: {str(e)}")
            raise Exception(f"Azure OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {str(e)}")
            raise Exception(f"Failed to get response from Azure OpenAI: {str(e)}")
    
    async def _regular_completion(self, messages: List[Dict], tools: List[Dict]) -> Dict[str, Any]:
        """Handle non-streaming completion"""
        try:
            logger.info("Making regular completion request to Azure OpenAI")
            logger.info(f"Using model: {config.AZURE_OPENAI_DEPLOYMENT_NAME}")
            logger.info(f"Tools available: {len(tools)}")
            
            # Make the API call with proper error handling
            response = await self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
            )
            
            logger.info(f"Received response from Azure OpenAI: {response.choices[0].finish_reason}")
            
            message = response.choices[0].message
            
            # Check if the model wants to call a tool
            if message.tool_calls:
                logger.info(f"Model requested {len(message.tool_calls)} tool calls")
                return await self._handle_tool_calls(messages, message, tools)
            
            return {
                "response": message.content,
                "usage": dict(response.usage) if response.usage else {},
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            logger.error(f"Error in _regular_completion: {str(e)}")
            raise
    
    async def _stream_completion(self, messages: List[Dict], tools: List[Dict]) -> AsyncGenerator[str, None]:
        """Handle streaming completion"""
        stream = await self.client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def _handle_tool_calls(self, messages: List[Dict], message, tools: List[Dict]) -> Dict[str, Any]:
        """Handle tool function calls"""
        # Add the assistant's message with tool calls to messages
        messages.append({
            "role": "assistant", 
            "content": message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                } for tool_call in message.tool_calls
            ]
        })
        
        # Execute tool calls
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool: {function_name} with args: {function_args}")
            
            # Call the tool
            try:
                tool_result = await self.tool_manager.execute_tool(function_name, function_args)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result)
                })
                
            except Exception as e:
                logger.error(f"Error executing tool {function_name}: {str(e)}")
                messages.append({
                    "role": "tool", 
                    "tool_call_id": tool_call.id,
                    "content": f"Error executing tool: {str(e)}"
                })
        
        # Get final response after tool execution
        final_response = await self.client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
        )
        
        return {
            "response": final_response.choices[0].message.content,
            "tool_calls": [tool_call.function.name for tool_call in message.tool_calls],
            "usage": dict(final_response.usage) if final_response.usage else {},
            "finish_reason": final_response.choices[0].finish_reason
        }


# Global service instance
azure_openai_service = AzureOpenAIService()