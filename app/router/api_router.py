from fastapi import APIRouter
from .routes import agent_service

router = APIRouter()

# Include the agent service router
router.include_router(agent_service.router, prefix="/agent", tags=["Agent Service"])
