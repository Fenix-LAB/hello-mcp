"""
FastAPI Server Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from config.logger_config import logger
from config.config import config
from app.router.api_router import router


def make_middleware() -> list[Middleware]:
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ]
    return middleware


def create_app() -> FastAPI:
    logger.info(f"SERVER: MCP Assistant API - env: {config.ENV}")
    app_ = FastAPI(
        title="MCP Assistant API",
        description="AI Assistant with Azure OpenAI and Custom Tools",
        version="1.0.0",
        docs_url=None if config.ENV == "production" else "/docs",
        redoc_url=None if config.ENV == "production" else "/redoc",
        middleware=make_middleware(),
    )
    
    # Include routers
    app_.include_router(router, prefix=config.ROUTE_PATH)
    
    logger.info("SERVER: Event 'start up'")

    @app_.on_event("startup")
    async def on_startup():
        logger.info("🚀 MCP Assistant API starting up...")
        logger.info(f"📊 Azure OpenAI configured: {bool(config.AZURE_OPENAI_ENDPOINT)}")
        logger.info(f"🔧 Environment: {config.ENV}")

    @app_.on_event("shutdown")
    async def on_shutdown():
        logger.info("📴 MCP Assistant API shutting down...")

    logger.info("SERVER: App created")
    return app_


app = create_app()
