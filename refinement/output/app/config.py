from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./booking.db"
    JWT_SECRET_KEY: str = "supersecretkeypleasechangemeinproduction1234567890123"
    JWT_REFRESH_SECRET_KEY: str = "supersecretrefreshkeypleasechangemeinproduction1234567890123"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()
