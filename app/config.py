from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Загружаем переменные из .env файла, если он есть
load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/db")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    EMAIL_USER: str | None = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore" # Игнорировать лишние переменные в .env

settings = Settings()