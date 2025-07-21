from fastapi import APIRouter
from .routes import agent_service, websocket_route

router = APIRouter()

# Include the agent service router
router.include_router(agent_service.router, prefix="/agent", tags=["Agent Service"])

# Include the websocket router
router.include_router(websocket_route.router, prefix="", tags=["WebSocket Voice Agent"])
