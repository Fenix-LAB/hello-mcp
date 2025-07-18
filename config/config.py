import os
import json

from pydantic_settings import BaseSettings


with open("config.json") as f:
    production_conf = json.load(f)

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

    # API CIVA
    CIVA_API_URL: str = production_conf["prod"]["civa_api"]["url"]
    CIVA_SECRET_KEY: str = production_conf["prod"]["civa_api"]["secret_key_token"]
    CIVA_ALGORITHM: str = production_conf["prod"]["civa_api"]["algorithm"]


class ProductionConfig(Config):
    DEBUG: bool = production_conf["prod"]["debug"]
    APP_HOST: str = production_conf["prod"]["app"]["host"]
    APP_PORT: str = production_conf["prod"]["app"]["port"]
    JWT_SECRET: str = production_conf["prod"]["jwt"]["api"]["secret_key"]
    JWT_ALGORITHM: str = production_conf["prod"]["jwt"]["api"]["algorithm"]
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = production_conf["prod"]["jwt"]["api"][
        "access_token_expire_minutes"
    ]
    EXCLUDED_URLS: list[str] = production_conf["prod"]["excluded_urls"]
    ROUTE_PATH: str = production_conf["prod"]["route_path"]

    # API CIVA
    CIVA_API_URL: str = production_conf["prod"]["civa_api"]["url"]
    CIVA_SECRET_KEY: str = production_conf["prod"]["civa_api"]["secret_key_token"]
    CIVA_ALGORITHM: str = production_conf["prod"]["civa_api"]["algorithm"]


class TestConfig(ProductionConfig):
    WRITER_DB_URL: str = "mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi_test"
    READER_DB_URL: str = "mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi_test"


class LocalConfig(Config):
    APP_HOST: str = "127.0.0.1"
    ONE_CORE_DB_NAME: str = "one-core-db"
    ONE_CORE_DB_USER: str = "postgres"
    ONE_CORE_DB_PASSWORD: str = "onecore77"
    ONE_CORE_DB_HOST: str = "localhost"
    ONE_CORE_DB_PORT: int = 5432
    WT_SECRET: str = production_conf["prod"]["jwt"]["api"]["secret_key"]
    JWT_ALGORITHM: str = production_conf["prod"]["jwt"]["api"]["algorithm"]
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = production_conf["prod"]["jwt"]["api"][
        "access_token_expire_minutes"
    ]
    EXCLUDED_URLS: list[str] = production_conf["prod"]["excluded_urls"]
    ROUTE_PATH: str = production_conf["prod"]["route_path"]

    # API CIVA
    CIVA_API_URL: str = production_conf["prod"]["civa_api"]["url"]
    CIVA_SECRET_KEY: str = production_conf["prod"]["civa_api"]["secret_key_token"]
    CIVA_ALGORITHM: str = production_conf["prod"]["civa_api"]["algorithm"]

def get_config():
    env = os.getenv("ENV", "local")
    config_type = {
        "test": TestConfig(),
        "local": LocalConfig(),
        "prod": ProductionConfig(),
    }
    return config_type[env]


config: Config = get_config()