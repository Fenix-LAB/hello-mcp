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
    usage: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[str]] = None


router = APIRouter()


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
        
        # Get response from Azure OpenAI
        result = await azure_openai_service.chat_completion(
            message=data.message,
            conversation_history=data.conversation_history,
            stream=data.stream
        )
        
        # Create response
        response = ChatResponse(
            response=result["response"],
            conversation_id=conversation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            usage=result.get("usage"),
            tool_calls=result.get("tool_calls")
        )
        
        logger.info(f"Chat response generated for conversation: {conversation_id}")
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
