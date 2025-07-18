import os
import json

from pydantic_settings import BaseSettings


try:
    with open("config.json") as f:
        production_conf = json.load(f)
except FileNotFoundError:
    production_conf = {"prod": {}}

class Config(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    JWT_SECRET_KEY: str = "your_secret_key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    EXCLUDED_URLS: list[str] = ["/api/auth/login", "/docs", "/redoc", "/openapi.json"]
    ROUTE_PATH: str = "/api"

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "https://apim-tp-test-001.azure-api.net/test-2")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "d28ff6f4f2654869a06cb75565a303ca")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
    
    # Assistant Configuration
    ASSISTANT_NAME: str = "MCP Assistant"
    ASSISTANT_DESCRIPTION: str = "A helpful AI assistant with custom tools"
    MAX_TOKENS: int = 1500
    TEMPERATURE: float = 0.7

    # API CIVA (keeping existing config)
    CIVA_API_URL: str = production_conf.get("prod", {}).get("civa_api", {}).get("url", "")
    CIVA_SECRET_KEY: str = production_conf.get("prod", {}).get("civa_api", {}).get("secret_key_token", "")
    CIVA_ALGORITHM: str = production_conf.get("prod", {}).get("civa_api", {}).get("algorithm", "")


class ProductionConfig(Config):
    DEBUG: bool = production_conf.get("prod", {}).get("debug", False)
    APP_HOST: str = production_conf.get("prod", {}).get("app", {}).get("host", "0.0.0.0")
    APP_PORT: int = production_conf.get("prod", {}).get("app", {}).get("port", 8080)
    JWT_SECRET: str = production_conf.get("prod", {}).get("jwt", {}).get("api", {}).get("secret_key", "")
    JWT_ALGORITHM: str = production_conf.get("prod", {}).get("jwt", {}).get("api", {}).get("algorithm", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = production_conf.get("prod", {}).get("jwt", {}).get("api", {}).get("access_token_expire_minutes", 60)
    EXCLUDED_URLS: list[str] = production_conf.get("prod", {}).get("excluded_urls", [])
    ROUTE_PATH: str = production_conf.get("prod", {}).get("route_path", "/api")


class TestConfig(ProductionConfig):
    WRITER_DB_URL: str = "mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi_test"
    READER_DB_URL: str = "mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi_test"


class LocalConfig(Config):
    APP_HOST: str = "127.0.0.1"
    # Azure OpenAI - Local Development
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com/")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "your-api-key-here")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")


def get_config():
    env = os.getenv("ENV", "local")
    config_type = {
        "test": TestConfig(),
        "local": LocalConfig(),
        "prod": ProductionConfig(),
    }
    return config_type[env]


config: Config = get_config()