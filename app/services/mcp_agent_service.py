"""
Agent Service using OpenAI Agents with Azure OpenAI as provider and MCP servers
"""
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
from openai import AsyncOpenAI
from agents import Agent, Runner, StreamEvent, set_default_openai_client
from openai.types.responses import ResponseTextDeltaEvent, ResponseOutputItemDoneEvent, ResponseFunctionToolCall
from agents import ToolCallOutputItem
from agents.mcp.server import MCPServerSse

from config.config import config
from config.logger_config import logger


class MCPAgentService:
    """Service to interact with Azure OpenAI using OpenAI Agents and MCP servers"""
    
    def __init__(self):
        try:
            logger.info(f"Initializing MCP Agent Service with Azure OpenAI")
            logger.info(f"Endpoint: {config.AZURE_OPENAI_ENDPOINT}")
            logger.info(f"Deployment: {config.AZURE_OPENAI_DEPLOYMENT_NAME}")
            logger.info(f"API Version: {config.AZURE_OPENAI_API_VERSION}")
            
            # Create isolated Azure OpenAI client
            self.client = self._create_isolated_client()
            
            # Set as default client for agents
            set_default_openai_client(self.client, use_for_tracing=False)
            
            # Initialize MCP servers
            self.mcp_servers = []
            asyncio.create_task(self._initialize_mcp_servers())
            
            self.system_prompt = """
You are a helpful AI assistant with access to various MCP (Model Context Protocol) servers that provide specialized tools and capabilities.

You can help users with:
- General information and questions
- File operations and data processing
- External API calls and integrations
- Task automation through MCP servers
- Real-time data retrieval

When a user asks for something that requires using an MCP server, analyze their request and use the appropriate MCP server capabilities to help them.
Always be helpful, accurate, and provide clear explanations of what you're doing.

Available MCP servers will be automatically connected and their tools will be available for use.
"""
            
            logger.info("MCP Agent Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Agent Service: {str(e)}")
            raise
    
    def _create_isolated_client(self) -> AsyncOpenAI:
        """Create an isolated Azure OpenAI client for the agent"""
        base_url = f"{config.AZURE_OPENAI_ENDPOINT}/openai/deployments/{config.AZURE_OPENAI_DEPLOYMENT_NAME}"
        
        return AsyncOpenAI(
            base_url=base_url,
            api_key=config.AZURE_OPENAI_API_KEY,
            default_headers={"api-key": config.AZURE_OPENAI_API_KEY},
            default_query={"api-version": config.AZURE_OPENAI_API_VERSION},
            timeout=30.0,
            max_retries=3
        )
    
    async def _initialize_mcp_servers(self):
        """Initialize MCP servers"""
        try:
            logger.info("Initializing MCP servers...")
            
            # Example MCP server - replace with your actual MCP server URLs
            example_mcp_servers = [
                {
                    "name": "deepwiki_mcp",
                    "url": "https://mcp.deepwiki.com/sse",
                    "description": "DeepWiki public MCP server for GitHub docs"
                },
                # Add more MCP servers here as needed
                # {
                #     "name": "weather_mcp", 
                #     "url": "http://localhost:3002",
                #     "description": "Weather data MCP server"
                # }
            ]
            
            for server_config in example_mcp_servers:
                try:
                    logger.info(f"Connecting to MCP server: {server_config['name']} at {server_config['url']}")
                    
                    # Create MCP server connection
                    mcp_server = MCPServerSse(params={"url": server_config["url"]})
                    await mcp_server.connect()
                    
                    self.mcp_servers.append({
                        "name": server_config["name"],
                        "server": mcp_server,
                        "description": server_config["description"]
                    })
                    
                    logger.info(f"Successfully connected to MCP server: {server_config['name']}")
                    
                except Exception as e:
                    logger.warning(f"Failed to connect to MCP server {server_config['name']}: {str(e)}")
                    continue
            
            logger.info(f"Initialized {len(self.mcp_servers)} MCP servers")
            
        except Exception as e:
            logger.error(f"Error initializing MCP servers: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test the connection to Azure OpenAI through the agent client"""
        try:
            logger.info("Testing MCP Agent Service connection...")
            
            # Test the Azure OpenAI connection
            response = await self.client.chat.completions.create(
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
        
        Args:
            message: User message
            conversation_history: Previous conversation messages
            stream: Whether to stream the response
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Response from the agent
        """
        try:
            logger.info(f"Processing chat completion with MCP Agent for user: {user_id}")
            
            # Prepare messages for the agent
            messages = self._prepare_messages(message, conversation_history)
            
            # Create agent with MCP servers
            agent = Agent(
                name="MCP Assistant",
                instructions=self.system_prompt,
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                mcp_servers=[server["server"] for server in self.mcp_servers]
            )
            
            logger.info(f"Created agent with {len(self.mcp_servers)} MCP servers")
            
            if stream:
                return await self._stream_completion(agent, messages)
            else:
                return await self._regular_completion(agent, messages)
                
        except Exception as e:
            logger.error(f"Error in MCP chat completion: {str(e)}")
            raise Exception(f"Failed to get response from MCP Agent: {str(e)}")
    
    def _prepare_messages(self, message: str, conversation_history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """Prepare messages for the agent"""
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
                else:
                    logger.warning(f"Invalid message format in history: {msg}")
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        logger.info(f"Prepared {len(messages)} messages for agent")
        return messages
    
    async def _regular_completion(self, agent: Agent, messages: List[Dict]) -> Dict[str, Any]:
        """Handle non-streaming completion with agent"""
        try:
            logger.info("Running agent with MCP servers...")
            
            # Run the agent
            result = Runner.run(
                starting_agent=agent,
                input=messages
            )
            
            # Extract the final response
            final_output = result.final_output if hasattr(result, 'final_output') else str(result)
            
            # Get MCP servers that were used
            mcp_servers_used = [server["name"] for server in self.mcp_servers]
            
            logger.info(f"Agent completed successfully")
            
            return {
                "response": final_output,
                "mcp_servers_used": mcp_servers_used,
                "usage": {},  # Agent usage info if available
                "finish_reason": "stop"
            }
            
        except Exception as e:
            logger.error(f"Error in _regular_completion: {str(e)}")
            raise
    
    async def _stream_completion(self, agent: Agent, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Handle streaming completion with agent"""
        try:
            logger.info("Running streamed agent with MCP servers...")
            
            result = Runner.run_streamed(
                starting_agent=agent,
                input=messages
            )
            
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    if event.data.delta:
                        yield event.data.delta
                elif event.type == "agent_updated_stream_event":
                    yield "[Agent processing...]"
                elif (
                    event.type == "raw_response_event"
                    and isinstance(event.data, ResponseOutputItemDoneEvent)
                    and isinstance(event.data.item, ResponseFunctionToolCall)
                ):
                    yield f"[MCP Call: {event.data.item.function.name}]"
                elif event.type == "run_item_stream_event" and isinstance(event.item, ToolCallOutputItem):
                    yield f"[MCP Result received]"
            
        except Exception as e:
            logger.error(f"Error in _stream_completion: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def get_mcp_servers_info(self) -> List[Dict[str, Any]]:
        """Get information about connected MCP servers"""
        return [
            {
                "name": server["name"],
                "description": server["description"],
                "status": "connected"
            }
            for server in self.mcp_servers
        ]
    
    async def add_mcp_server(self, name: str, url: str, description: str = "") -> bool:
        """Add a new MCP server dynamically"""
        try:
            logger.info(f"Adding new MCP server: {name} at {url}")
            
            mcp_server = MCPServerSse(url=url)
            await mcp_server.connect()
            
            self.mcp_servers.append({
                "name": name,
                "server": mcp_server,
                "description": description
            })
            
            logger.info(f"Successfully added MCP server: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add MCP server {name}: {str(e)}")
            return False
    
    async def remove_mcp_server(self, name: str) -> bool:
        """Remove an MCP server"""
        try:
            for i, server in enumerate(self.mcp_servers):
                if server["name"] == name:
                    # Disconnect the server if it has a disconnect method
                    if hasattr(server["server"], "disconnect"):
                        await server["server"].disconnect()
                    
                    self.mcp_servers.pop(i)
                    logger.info(f"Removed MCP server: {name}")
                    return True
            
            logger.warning(f"MCP server not found: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove MCP server {name}: {str(e)}")
            return False


# Global service instance
mcp_agent_service = MCPAgentService()
