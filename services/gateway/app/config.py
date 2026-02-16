from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PI Gateway"
    auth_service_url: str = "http://auth_service:8000"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"


settings = Settings()
