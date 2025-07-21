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
from agents.mcp.server import MCPServerSse
from agents.model_settings import ModelSettings
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
            
            # Initialize MCP servers containers
            self.mcp_servers = {}
            self.connected_servers = []
            self._servers_initialized = False
            
            # System prompt for the agent
            self.system_prompt = """
You are a helpful AI assistant with access to MCP (Model Context Protocol) servers that provide specialized tools.

Available capabilities:
- General information and assistance
- Access to external services through MCP servers
- Data processing and analysis
- Task automation
- Real-time data retrieval from connected MCP servers

You have access to MCP servers that can:
- Search and retrieve GitHub repository information
- Access documentation and README files
- Perform external API calls
- Process and analyze data

When a user asks for something that requires external tools or services, use the appropriate MCP server to help them.
Always be helpful, accurate, and provide clear explanations of what you're doing.
"""
            
            logger.info("MCP Agent Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Agent Service: {str(e)}")
            raise
            
    async def _initialize_mcp_servers(self):
        """Initialize and connect MCP servers for the agent"""
        try:
            logger.info("Initializing MCP servers...")
            
            # Configuration for MCP servers
            mcp_server_configs = [
                {
                    "name": "deepwiki_mcp",
                    "url": "https://mcp.deepwiki.com/sse",
                    "description": "DeepWiki MCP Server for GitHub documentation and repository information",
                    "headers": {
                        "User-Agent": "MCP-Agent/1.0"
                    },
                    "timeout": 10.0,
                    "sse_read_timeout": 300.0
                }
                # Puedes agregar más servidores MCP aquí
            ]
            
            for server_config in mcp_server_configs:
                try:
                    logger.info(f"Connecting to MCP server: {server_config['name']} at {server_config['url']}")
                    
                    # Create MCP server connection
                    mcp_server = MCPServerSse(
                        params={
                            "url": server_config["url"],
                            "headers": server_config.get("headers", {}),
                            "timeout": server_config.get("timeout", 5.0),
                            "sse_read_timeout": server_config.get("sse_read_timeout", 300.0)
                        },
                        cache_tools_list=True,
                        name=server_config["name"],
                        client_session_timeout_seconds=30.0
                    )
                    
                    # Connect to the MCP server
                    try:
                        await mcp_server.connect()
                        logger.info(f"Successfully connected to MCP server: {server_config['name']}")
                        
                        # Store the MCP server instance
                        self.mcp_servers[server_config["name"]] = mcp_server
                        
                        # Add to connected servers list
                        self.connected_servers.append({
                            "name": server_config["name"],
                            "url": server_config["url"],
                            "description": server_config["description"],
                            "status": "connected",
                            "server_instance": mcp_server
                        })
                        
                        logger.info(f"Successfully configured MCP server: {server_config['name']}")
                        
                    except Exception as connect_error:
                        logger.warning(f"Failed to connect to MCP server {server_config['name']}: {str(connect_error)}")
                        continue
                    
                except Exception as e:
                    logger.warning(f"Failed to configure MCP server {server_config['name']}: {str(e)}")
                    continue
            
            logger.info(f"Initialized {len(self.mcp_servers)} MCP servers")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP servers: {str(e)}")
    
    async def _ensure_mcp_servers_initialized(self):
        """Ensure MCP servers are initialized and connected"""
        if not self._servers_initialized:
            logger.info("Initializing MCP servers on first use...")
            await self._initialize_mcp_servers()
            self._servers_initialized = True
    
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
            }
            
            # Use MCP Agent with MCP servers
            try:
                # Create a placeholder agent for context (the real one is created in _regular_completion)
                agent = None
                
                if stream:
                    # For streaming, return the async generator directly
                    return self._stream_completion(agent, messages, context)
                else:
                    return await self._regular_completion(agent, messages, context)
                    
            except Exception as agent_error:
                logger.error(f"MCP Agent failed: {str(agent_error)}")
                raise Exception(f"Failed to process request with MCP Agent: {str(agent_error)}")
                
        except Exception as e:
            logger.error(f"Error in MCP chat completion: {str(e)}")
            raise Exception(f"Failed to process chat completion: {str(e)}")
    
    async def _create_agent(self) -> Agent:
        """Create an OpenAI Agent with MCP servers"""
        try:
            # Ensure MCP servers are initialized
            await self._ensure_mcp_servers_initialized()
            
            # Get list of MCP servers
            mcp_server_list = [server["server_instance"] for server in self.connected_servers]
            
            if not mcp_server_list:
                raise Exception("No MCP servers available")
            
            agent = Agent(
                name="MCP Assistant",
                instructions=self.system_prompt,
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                mcp_servers=mcp_server_list
            )
            
            logger.info(f"Created agent with {len(mcp_server_list)} MCP servers")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise
    
    async def _regular_completion(self, agent: Agent, messages: List[Dict], context: Dict) -> Dict[str, Any]:
        try:
            logger.info("Running MCP agent for regular completion...")
            
            user_message = messages[-1]["content"] if messages else "Hello"

            print(f"User message: {user_message} type: {type(user_message)}")

            async with MCPServerSse(
                name="DeepWiki MCP Server",
                params={
                    "url": "http://127.0.0.1:8000/sse",
                },
            ) as mcp_server:
                
                agent = Agent(
                    name="Assistant",
                    instructions="Use the tools to answer the questions.",
                    model="gpt-4o",  # Usar deployment name de Azure
                    mcp_servers=[mcp_server],
                    model_settings=ModelSettings(tool_choice="auto")
                )

                print(f"Agent created: {agent.name}")
                
                try:
                    runner_result = await Runner.run(
                        starting_agent=agent,
                        input=user_message  # Asegúrate que esto sea un string
                    )
                except Exception as runner_error:
                    print(f"Runner error details: {str(runner_error)}")
                    print(f"Runner error type: {type(runner_error)}")
                    raise runner_error

                print(f"Runner result: {runner_result} type: {type(runner_result)}")
                
                response_content = runner_result.final_output or str(runner_result)

            logger.info(f"MCP agent completed successfully - Response length: {len(str(response_content))} chars")
            
            return {
                "response": str(response_content),
                "usage": {
                    "total_tokens": getattr(runner_result, 'total_tokens', 0),
                    "prompt_tokens": getattr(runner_result, 'prompt_tokens', 0),
                    "completion_tokens": getattr(runner_result, 'completion_tokens', 0)
                },
                "tool_calls": getattr(runner_result, 'tool_calls', []),
                "mcp_servers_used": ["deepwiki_mcp"],
                "finish_reason": "stop"
            }
            
        except Exception as e:
            logger.error(f"Error in _regular_completion: {str(e)}")
            raise Exception(f"MCP Agent completion failed: {str(e)}")

    
    async def _stream_completion(self, agent: Agent, messages: List[Dict], context: Dict) -> AsyncGenerator[str, None]:
        """Handle streaming completion with MCP servers"""
        try:
            logger.info("Running MCP agent for streaming completion...")
            
            # Use the last user message as input for the runner
            user_message = messages[-1]["content"] if messages else "Hello"
            
            # Use context manager for MCP server connection (like in the official example)
            async with MCPServerSse(
                name="DeepWiki MCP Server",
                params={
                    "url": "https://mcp.deepwiki.com/sse",
                },
            ) as mcp_server:
                
                # Create agent with MCP server and ModelSettings like the example
                agent = Agent(
                    name="Assistant",
                    instructions="Use the tools to answer the questions.",
                    model="gpt-4o",  # Use simple model name instead of deployment name
                    mcp_servers=[mcp_server],
                    model_settings=ModelSettings(tool_choice="auto")  # Change to auto instead of required
                )
                
                # Run the agent with MCP servers
                runner_result = await Runner.run(
                    starting_agent=agent,
                    input=user_message
                )
                
                # Extract the response from the runner result
                response_content = runner_result.final_output or str(runner_result)
            
            response_text = str(response_content)
            
            # Simulate streaming by yielding words
            words = response_text.split()
            for word in words:
                yield f"{word} "
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Error in _stream_completion: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def get_mcp_servers_info(self) -> List[Dict[str, Any]]:
        """Get information about connected MCP servers"""
        return self.connected_servers
    
    async def stream_chat_completion(self, message: str, history: List[Dict] = None) -> AsyncGenerator[str, None]:
        """Stream chat completion with MCP agent"""
        messages = history or []
        messages.append({"role": "user", "content": message})
        
        try:
            # Use MCP agent for streaming
            agent = await self._create_agent()
            async for chunk in self._stream_completion(agent, messages, {}):
                yield chunk
        
        except Exception as e:
            logger.error(f"Error in stream_chat_completion: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def add_mcp_server(self, name: str, url: str, description: str = "") -> bool:
        """Add a new MCP server"""
        try:
            logger.info(f"Adding new MCP server: {name} at {url}")
            
            # Create new MCP server connection
            new_mcp_server = MCPServerSse(
                params={
                    "url": url,
                    "headers": {"User-Agent": "MCP-Agent/1.0"},
                    "timeout": 10.0,
                    "sse_read_timeout": 300.0
                },
                cache_tools_list=True,
                name=name,
                client_session_timeout_seconds=30.0
            )
            
            # Connect to the MCP server
            await new_mcp_server.connect()
            
            # Add to MCP servers dictionary
            self.mcp_servers[name] = new_mcp_server
            
            # Add to connected servers list
            new_server = {
                "name": name,
                "url": url,
                "description": description,
                "status": "connected",
                "server_instance": new_mcp_server
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