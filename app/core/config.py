import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Environment
    ENV: str = "production"

    # API Config
    API_TITLE: str = "Cisnatura API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for Cisnatura e-commerce application"
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@db:5432/cisnatura"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security & JWT
    SECRET_KEY: str = "your-secret-key-change-in-production-PLEASE"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Email / SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@cisnatura.com"
    FROM_NAME: str = "Cisnatura"
    
    # Frontend URL (para links de verificación)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Payment Provider Configuration
    PAYMENT_PROVIDER: str = "stripe"
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Upload Configuration
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "webp"}
    WEBP_QUALITY: int = 85
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignorar variables de env extra
    )

settings = Settings()
