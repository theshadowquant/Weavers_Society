import os

class Settings:
    PROJECT_NAME: str = "Karnataka Handloom Cooperative Management Platform"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.environ.get("SOCIETY_SECRET_KEY", "karnataka-handloom-super-secret-key-2026-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours for cooperative work shifts
    ALGORITHM: str = "HS256"
    DEFAULT_LANGUAGE: str = "kn"
    DEFAULT_CURRENCY: str = "INR"

settings = Settings()
