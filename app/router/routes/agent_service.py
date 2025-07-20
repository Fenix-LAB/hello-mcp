"""API Router definition for Agent Service."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from config.logger_config import logger
from config.config import config
from app.services.azure_openai_service import azure_openai_service
from app.services.mcp_agent_service import mcp_agent_service


class RequestData(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    stream: Optional[bool] = False
    conversation_history: Optional[List[Dict[str, str]]] = None
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = "default_session"


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str
    usage: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[str]] = None
    mcp_servers_used: Optional[List[str]] = None


class MCPServerRequest(BaseModel):
    name: str
    url: str
    description: Optional[str] = ""


router = APIRouter()


@router.get("/diagnose")
async def diagnose_azure_openai():
    """
    Diagnose Azure OpenAI configuration and connectivity.
    """
    try:
        # Check configuration
        config_status = {
            "endpoint_configured": bool(config.AZURE_OPENAI_ENDPOINT),
            "api_key_configured": bool(config.AZURE_OPENAI_API_KEY),
            "deployment_configured": bool(config.AZURE_OPENAI_DEPLOYMENT_NAME),
            "endpoint": config.AZURE_OPENAI_ENDPOINT,
            "api_version": config.AZURE_OPENAI_API_VERSION,
            "deployment": config.AZURE_OPENAI_DEPLOYMENT_NAME
        }
        
        # Test connection
        connection_test = await azure_openai_service.test_connection()
        
        return {
            "status": "healthy" if connection_test else "unhealthy",
            "configuration": config_status,
            "connection_test": connection_test,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in diagnose endpoint: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: Request, data: RequestData
) -> ChatResponse:
    """
    Chat with the AI assistant using Azure OpenAI with custom tools.
    
    - **message**: The user's message
    - **conversation_id**: Optional conversation ID to maintain context
    - **stream**: Whether to stream the response (currently returns regular response)
    - **conversation_history**: Previous conversation messages for context
    """
    try:
        logger.info(f"Received chat request: {data.message[:100]}...")
        
        # Generate conversation ID if not provided
        conversation_id = data.conversation_id or str(uuid4())

        logger.info(f"Processing chat for conversation ID: {conversation_id}")
        
        # Get response from Azure OpenAI
        result = await azure_openai_service.chat_completion(
            message=data.message,
            conversation_history=data.conversation_history,
            stream=data.stream
        )

        logger.info(f"Result received for conversation: {result}")

        logger.info(
            f"Chat response details: {result.get('response', '')[:100]}... "
            f"Usage: {result.get('usage', {})}, Tool Calls: {result.get('tool_calls', [])}"
        )
        
        # Create response
        response = ChatResponse(
            response=result["response"],
            conversation_id=conversation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            # usage=result.get("usage"),
            tool_calls=result.get("tool_calls")
        )
        
        logger.info(f"Chat response generated for conversation: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing chat request: {str(e)}"
        )


@router.post("/chat-stream")
async def chat_stream_endpoint(
    request: Request, data: RequestData
) -> StreamingResponse:
    """
    Chat with streaming response (placeholder for future implementation).
    """
    
    async def generate_stream():
        try:
            # For now, return a simple streaming response
            # TODO: Implement actual streaming with Azure OpenAI
            response = await azure_openai_service.chat_completion(
                message=data.message,
                conversation_history=data.conversation_history,
                stream=False  # For now, convert to streaming format
            )
            
            # Simulate streaming by chunking the response
            words = response["response"].split()
            for i, word in enumerate(words):
                if i == 0:
                    yield f"data: {word}"
                else:
                    yield f"data: {word}"
                await asyncio.sleep(0.05)  # Small delay to simulate streaming
            
            yield "data: [DONE]"
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield f"data: Error: {str(e)}"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/tools")
async def list_tools():
    """
    List all available tools for the assistant.
    """
    try:
        tools = azure_openai_service.tool_manager.list_tools()
        return {
            "tools": tools,
            "count": len(tools),
            "description": "Available tools for the AI assistant"
        }
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the agent service.
    """
    return {
        "status": "healthy",
        "service": "MCP Agent Service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "azure_openai_configured": bool(azure_openai_service.client)
    }


# =================== MCP AGENT ENDPOINTS ===================

@router.post("/mcp/chat", response_model=ChatResponse)
async def mcp_chat_endpoint(
    request: Request, data: RequestData
) -> ChatResponse:
    """
    Chat with the AI assistant using MCP Agent (OpenAI Agents + Azure OpenAI + MCP servers).
    
    This endpoint uses OpenAI Agents with Azure OpenAI as the provider and connects to MCP servers
    instead of using traditional function calling tools.
    
    - **message**: The user's message
    - **conversation_id**: Optional conversation ID to maintain context
    - **stream**: Whether to stream the response (currently returns regular response)
    - **conversation_history**: Previous conversation messages for context
    - **user_id**: User identifier for session management
    - **session_id**: Session identifier for conversation context
    """
    try:
        logger.info(f"Received MCP chat request: {data.message[:100]}...")
        
        # Generate conversation ID if not provided
        conversation_id = data.conversation_id or str(uuid4())

        logger.info(f"Processing MCP chat for conversation ID: {conversation_id}")
        
        # Get response from MCP Agent Service
        result = await mcp_agent_service.chat_completion(
            message=data.message,
            conversation_history=data.conversation_history,
            stream=False,  # Force non-streaming for regular endpoint
            user_id=data.user_id,
            session_id=data.session_id
        )

        logger.info(f"MCP Agent result received for conversation: {conversation_id}")
        
        # Create response
        response = ChatResponse(
            response=result["response"],
            conversation_id=conversation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            # usage=result.get("usage"),
            tool_calls=result.get("tool_calls"),
            mcp_servers_used=result.get("mcp_servers_used")
        )
        
        logger.info(f"MCP chat response generated for conversation: {conversation_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in MCP chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing MCP chat request: {str(e)}"
        )


@router.post("/mcp/chat-stream")
async def mcp_chat_stream_endpoint(
    request: Request, data: RequestData
) -> StreamingResponse:
    """
    Chat with streaming response using MCP Agent.
    """
    
    async def generate_mcp_stream():
        try:
            logger.info(f"Starting MCP streaming chat for: {data.message[:50]}...")
            
            # Get streaming response from MCP Agent Service
            stream_generator = await mcp_agent_service.chat_completion(
                message=data.message,
                conversation_history=data.conversation_history,
                stream=True,  # Enable streaming
                user_id=data.user_id,
                session_id=data.session_id
            )
            
            # stream_generator should be an async generator
            async for chunk in stream_generator:
                yield f"data: {chunk}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in MCP streaming chat: {str(e)}")
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate_mcp_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/mcp/servers")
async def list_mcp_servers():
    """
    List all connected MCP servers.
    """
    try:
        servers = await mcp_agent_service.get_mcp_servers_info()
        return {
            "mcp_servers": servers,
            "count": len(servers),
            "description": "Connected MCP servers"
        }
    except Exception as e:
        logger.error(f"Error listing MCP servers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/servers")
async def add_mcp_server(server_request: MCPServerRequest):
    """
    Add a new MCP server dynamically.
    
    - **name**: Unique name for the MCP server
    - **url**: URL of the MCP server
    - **description**: Optional description of the server capabilities
    """
    try:
        logger.info(f"Adding MCP server: {server_request.name} at {server_request.url}")
        
        success = await mcp_agent_service.add_mcp_server(
            name=server_request.name,
            url=server_request.url,
            description=server_request.description
        )
        
        if success:
            return {
                "status": "success",
                "message": f"MCP server '{server_request.name}' added successfully",
                "server": {
                    "name": server_request.name,
                    "url": server_request.url,
                    "description": server_request.description
                }
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to add MCP server '{server_request.name}'"
            )
        
    except Exception as e:
        logger.error(f"Error adding MCP server: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mcp/servers/{server_name}")
async def remove_mcp_server(server_name: str):
    """
    Remove an MCP server.
    
    - **server_name**: Name of the MCP server to remove
    """
    try:
        logger.info(f"Removing MCP server: {server_name}")
        
        success = await mcp_agent_service.remove_mcp_server(server_name)
        
        if success:
            return {
                "status": "success",
                "message": f"MCP server '{server_name}' removed successfully"
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"MCP server '{server_name}' not found"
            )
        
    except Exception as e:
        logger.error(f"Error removing MCP server: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/diagnose")
async def diagnose_mcp_agent():
    """
    Diagnose MCP Agent Service configuration and connectivity.
    """
    try:
        # Check MCP Agent Service configuration
        config_status = {
            "azure_openai_configured": bool(config.AZURE_OPENAI_ENDPOINT and config.AZURE_OPENAI_API_KEY),
            "endpoint": config.AZURE_OPENAI_ENDPOINT,
            "api_version": config.AZURE_OPENAI_API_VERSION,
            "deployment": config.AZURE_OPENAI_DEPLOYMENT_NAME
        }
        
        # Test connection
        connection_test = await mcp_agent_service.test_connection()
        
        # Get MCP servers info
        mcp_servers = await mcp_agent_service.get_mcp_servers_info()
        
        return {
            "status": "healthy" if connection_test else "unhealthy",
            "configuration": config_status,
            "connection_test": connection_test,
            "mcp_servers": mcp_servers,
            "mcp_servers_count": len(mcp_servers),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in MCP diagnose endpoint: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }