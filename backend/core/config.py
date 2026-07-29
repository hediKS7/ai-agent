from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: Optional[str] = None
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Only Groq and Mistral
    groq_api_key: str
    mistral_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()