Implement comprehensive secret validation at application startup:

1. Create a configuration validation module at /src/api/config.py:
   ```python
   from pydantic import BaseSettings, validator

   class Settings(BaseSettings):
       DATABASE_URL: str
       CORS_ORIGINS: str
       LOG_LEVEL: str = "INFO"

       # AI Provider Keys (at least one required)
       ANTHROPIC_API_KEY: Optional[str] = None
       OPENAI_API_KEY: Optional[str] = None
       GOOGLE_API_KEY: Optional[str] = None

       @validator('DATABASE_URL')
       def validate_database_url(cls, v):
           if not v or v == "":
               raise ValueError("DATABASE_URL must be set")
           return v

       def validate_at_least_one_ai_provider(self):
           if not any([self.ANTHROPIC_API_KEY, self.OPENAI_API_KEY, self.GOOGLE_API_KEY]):
               raise ValueError("At least one AI provider API key must be configured")

       class Config:
           env_file = '.env'
Update /src/api/main.py to validate settings at startup:

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate configuration first
    try:
        settings = Settings()
        settings.validate_at_least_one_ai_provider()
        logger.info(f"Configuration validated successfully")
        logger.info(f"Database: {settings.DATABASE_URL[:20]}...")
        logger.info(f"AI Providers available: {', '.join(...)}")
    except ValidationError as e:
        logger.critical(f"Configuration validation failed: {e}")
        raise
Update dependencies.py to use Settings

Add configuration test at /tests/unit/api/test_config.py

Document required environment variables in /docs/deployment/

This ensures "fail fast" at startup rather than cryptic runtime failures.