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
    
    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-PLEASE")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Email / SMTP Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", os.getenv("SMTP_USER", "noreply@cisnatura.com"))
    FROM_NAME: str = os.getenv("FROM_NAME", "Cisnatura")
    
    # Frontend URL (para links de verificación)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Payment Provider Configuration
    PAYMENT_PROVIDER: str = os.getenv("PAYMENT_PROVIDER", "stripe")
    
    # Stripe
    STRIPE_API_KEY: str = os.getenv("STRIPE_SECRET_KEY", os.getenv("STRIPE_API_KEY", ""))
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    

    
    # Upload Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads")
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "webp"}
    WEBP_QUALITY: int = 85
    
    class Config:
        env_file = ".env"

settings = Settings()
