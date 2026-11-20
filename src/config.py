from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Ecommerce API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    PAYMENT_PROVIDER: str = "zarinpal"
    ZARINPAL_MERCHANT_ID: str = ""
    ZARINPAL_SANDBOX: bool = True
    PAYMENT_CALLBACK_BASE_URL: str = "http://localhost:8000/api/v1/payments/zarinpal/callback"
    PAYMENT_HTTP_TIMEOUT_SECONDS: int = 15
    PAYMENT_EXPIRY_MINUTES: int = 20
    PAYMENT_MIN_AMOUNT_RIAL: int = 10000
    PAYMENT_MAX_AMOUNT_RIAL: int = 500_000_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
