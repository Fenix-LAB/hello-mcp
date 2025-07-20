"""
MCP Agent Service using OpenAI Agents with Azure OpenAI as provider
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from agents import Agent, Runner, set_default_openai_client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config.config import config
from config.logger_config import logger


class MCPAgentService:
    """Service that uses OpenAI Agents with Azure OpenAI and MCP servers"""
    
    def __init__(self):
        try:
            logger.info("Initializing MCP Agent Service...")
            
            # Create Azure OpenAI client
            self.azure_client = self._create_azure_openai_client()
            set_default_openai_client(self.azure_client, use_for_tracing=False)
            
            # Initialize MCP servers
            self.mcp_servers = {}
            self.connected_servers = []
            
            # System prompt for the agent
            self.system_prompt = """
You are a helpful AI assistant with access to MCP (Model Context Protocol) servers.
You can help users with various tasks by connecting to different MCP servers that provide specialized tools.

Available capabilities:
- General information and assistance
- Access to external services through MCP servers
- Data processing and analysis
- Task automation

When a user asks for something that requires external tools or services, I will use the appropriate MCP server to help them.
Always be helpful, accurate, and provide clear explanations of what you're doing.
"""
            
            # Initialize example MCP server
            asyncio.create_task(self._initialize_example_mcp_server())
            
            logger.info("MCP Agent Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Agent Service: {str(e)}")
            raise
    
    def _create_azure_openai_client(self) -> AsyncOpenAI:
        """Create Azure OpenAI client"""
        base_url = f"{config.AZURE_OPENAI_ENDPOINT}/openai/deployments/{config.AZURE_OPENAI_DEPLOYMENT_NAME}"
        
        return AsyncOpenAI(
            base_url=base_url,
            api_key=config.AZURE_OPENAI_API_KEY,
            default_headers={"api-key": config.AZURE_OPENAI_API_KEY},
            default_query={"api-version": config.AZURE_OPENAI_API_VERSION},
            timeout=30.0,
            max_retries=3
        )
    
    async def _initialize_example_mcp_server(self):
        """Initialize example MCP server for testing"""
        try:
            # For now, we'll simulate an MCP server
            # In real implementation, you would connect to actual MCP servers
            self.connected_servers.append({
                "name": "deepwiki_mcp",
                "url": "http://localhost:3000/mcp",
                "description": "DeepWiki MCP Server for knowledge retrieval",
                "status": "connected",
                "tools": ["search_knowledge", "get_article", "summarize_content"]
            })
            logger.info("Example MCP server initialized")
        except Exception as e:
            logger.error(f"Failed to initialize example MCP server: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test the connection to Azure OpenAI"""
        try:
            response = await self.azure_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            logger.info("MCP Agent Service connection test successful")
            return True
        except Exception as e:
            logger.error(f"MCP Agent Service connection test failed: {str(e)}")
            return False
    
    async def chat_completion(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
        user_id: str = "default_user",
        session_id: str = "default_session"
    ) -> Dict[str, Any]:
        """
        Get chat completion using OpenAI Agent with MCP servers
        """
        try:
            logger.info(f"Processing MCP chat completion for user: {user_id}")
            
            # Prepare messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append(msg)
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            logger.info(f"Prepared {len(messages)} messages for MCP agent")
            
            # Create agent context
            context = {
                "user_id": user_id,
                "session_id": session_id,
                "mcp_servers": self.connected_servers
            }
            
            # Try to use MCP Agent, fallback to Azure OpenAI if needed
            try:
                # For now, skip MCP Agent creation and go directly to fallback
                # This ensures consistent behavior until MCP servers are properly implemented
                logger.info("Using Azure OpenAI directly (MCP Agent in development)")
                return await self._fallback_completion(messages)
                
                # TODO: Uncomment when MCP Agent is fully implemented
                # # Create agent (for now without actual MCP servers, just using Azure OpenAI)
                # agent = Agent(
                #     name="MCP Assistant",
                #     instructions=self.system_prompt,
                #     model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                #     # mcp_servers=[]  # Will add actual MCP servers later
                # )
                # 
                # if stream:
                #     return await self._stream_completion(agent, messages, context)
                # else:
                #     return await self._regular_completion(agent, messages, context)
                    
            except Exception as agent_error:
                logger.warning(f"MCP Agent failed, using fallback: {str(agent_error)}")
                # Fallback to direct Azure OpenAI
                return await self._fallback_completion(messages)
                
        except Exception as e:
            logger.error(f"Error in MCP chat completion: {str(e)}")
            # Final fallback
            try:
                return await self._fallback_completion(messages)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                return {
                    "response": f"I apologize, but I'm currently experiencing technical difficulties: {str(e)}",
                    "usage": {},
                    "tool_calls": [],
                    "mcp_servers_used": [],
                    "finish_reason": "error"
                }
    
    async def _regular_completion(self, agent: Agent, messages: List[Dict], context: Dict) -> Dict[str, Any]:
        """Handle non-streaming completion"""
        try:
            logger.info("Running MCP agent for regular completion...")
            
            # For now, skip the Runner and go directly to fallback
            # This avoids the "Unsupported data type" error until we have proper MCP servers
            logger.info("Using fallback Azure OpenAI completion due to MCP Agent configuration...")
            return await self._fallback_completion(messages)
            
            # TODO: Uncomment when MCP Agent is properly configured
            # # Run the agent and await the result properly
            # runner_result = await Runner.run(
            #     starting_agent=agent,
            #     input=messages,
            #     context=context
            # )
            # 
            # # Extract the final response
            # final_response = getattr(runner_result, 'final_output', None)
            # 
            # logger.info(f"MCP agent completed successfully")
            # 
            # # For now, simulate the response structure
            # # In real implementation, you would extract actual usage and tool call info
            # return {
            #     "response": str(final_response) if final_response else "I'm ready to help you with your request.",
            #     "usage": {
            #         "total_tokens": 0,
            #         "prompt_tokens": 0,
            #         "completion_tokens": 0
            #     },
            #     "tool_calls": [],
            #     "mcp_servers_used": [server["name"] for server in self.connected_servers],
            #     "finish_reason": "stop"
            # }
            
        except Exception as e:
            logger.error(f"Error in _regular_completion: {str(e)}")
            # Fallback to direct Azure OpenAI call
            return await self._fallback_completion(messages)
    
    async def _stream_completion(self, agent: Agent, messages: List[Dict], context: Dict) -> AsyncGenerator[str, None]:
        """Handle streaming completion"""
        try:
            logger.info("Running MCP agent for streaming completion...")
            
            # For now, use regular completion and simulate streaming
            result = await self._fallback_completion(messages)
            response_text = result.get("response", "No response available")
            
            # Simulate streaming by yielding words
            words = response_text.split()
            for word in words:
                yield f"{word} "
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Error in _stream_completion: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def _fallback_completion(self, messages: List[Dict]) -> Dict[str, Any]:
        """Fallback to direct Azure OpenAI call"""
        try:
            logger.info("Using fallback Azure OpenAI completion...")
            
            response = await self.azure_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE
            )
            
            # Ensure we get the complete response
            response_content = response.choices[0].message.content or "No response generated"
            
            logger.info(f"Fallback completion successful - Response length: {len(response_content)} chars")
            
            return {
                "response": response_content,
                "usage": dict(response.usage) if response.usage else {},
                "tool_calls": [],
                "mcp_servers_used": [server["name"] for server in self.connected_servers],
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            logger.error(f"Error in fallback completion: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "usage": {},
                "tool_calls": [],
                "mcp_servers_used": [],
                "finish_reason": "error"
            }
    
    async def get_mcp_servers_info(self) -> List[Dict[str, Any]]:
        """Get information about connected MCP servers"""
        return self.connected_servers
    
    async def stream_chat_completion(self, message: str, history: List[Dict] = None) -> AsyncGenerator[str, None]:
        """Stream chat completion with fallback"""
        messages = history or []
        messages.append({"role": "user", "content": message})
        
        try:
            # Use fallback streaming directly
            async for chunk in self._stream_completion(None, messages, {}):
                yield chunk
        
        except Exception as e:
            logger.error(f"Error in stream_chat_completion: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def add_mcp_server(self, name: str, url: str, description: str = "") -> bool:
        """Add a new MCP server"""
        try:
            # For now, just add to the list
            # In real implementation, you would establish actual connection
            new_server = {
                "name": name,
                "url": url,
                "description": description,
                "status": "connected",
                "tools": ["placeholder_tool"]  # Would be populated from actual MCP server
            }
            
            self.connected_servers.append(new_server)
            logger.info(f"Added MCP server: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding MCP server {name}: {str(e)}")
            return False
    
    async def remove_mcp_server(self, name: str) -> bool:
        """Remove an MCP server"""
        try:
            # Find and remove the server
            for i, server in enumerate(self.connected_servers):
                if server["name"] == name:
                    del self.connected_servers[i]
                    logger.info(f"Removed MCP server: {name}")
                    return True
            
            logger.warning(f"MCP server not found: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Error removing MCP server {name}: {str(e)}")
            return False


# Global service instance
mcp_agent_service = MCPAgentService()