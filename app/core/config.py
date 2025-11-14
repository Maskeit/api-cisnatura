import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Config
    API_TITLE: str = "Cisnatura API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for Cisnatura e-commerce application"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/cisnatura")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Stripe
    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    class Config:
        env_file = ".env"

settings = Settings()
