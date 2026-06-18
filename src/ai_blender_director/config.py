from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    comfy_url: str = "http://127.0.0.1:8188"
    blender_executable: str = "blender"
    server_port: int = 8000
    server_host: str = "127.0.0.1"
    openrouter_api_key: str | None = None
    cors_allow_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
