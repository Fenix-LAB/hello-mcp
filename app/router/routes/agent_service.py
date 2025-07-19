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


class RequestData(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    stream: Optional[bool] = False
    conversation_history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str
    # usage: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[str]] = None


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