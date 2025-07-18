"""API Router definition."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

class RequestData(BaseModel):
    message: str


router = APIRouter()


@router.post("/agent")
async def chat_endpoint(
    request: Request, data: RequestData
) -> StreamingResponse:
    """Allows to chat with your data.

    """

    # Code here


    return HTTPException(
        status_code=501, detail="Chat without stream is not implemented."
    )
