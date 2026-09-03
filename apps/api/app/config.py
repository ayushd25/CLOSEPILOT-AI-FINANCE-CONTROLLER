from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "closepilot"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.0

    RAZORPAY_MODE: str = "test"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    RAZORPAY_TIMEOUT_SECONDS: float = 30.0
    RAZORPAY_MAX_RETRIES: int = 3
    RAZORPAY_PAGE_SIZE: int = 100

    CORS_ORIGINS: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
