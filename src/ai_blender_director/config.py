from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    comfy_url: str = "http://127.0.0.1:8188"
    blender_executable: str = "blender"
    server_port: int = 8000
    server_host: str = "127.0.0.1"
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemini-2.5-flash"
    # Director Agent endurecido con Instructor. Opt-in: muchos modelos (p.ej.
    # gemini-2.5-flash) no emiten bien el schema anidado de tool-calling y
    # devuelven shots como strings; el JSON-mode clásico es más robusto y es el
    # default. Actívalo solo con modelos fuertes en structured outputs.
    director_use_instructor: bool = False
    cors_allow_origins: str = "http://127.0.0.1:8000,http://localhost:8000"

    # Síntesis de voz (TTS). "piper" es el motor local por defecto.
    # "xtts" usa el CLI de Coqui (clonación, español); "command" usa una
    # plantilla libre en tts_command con placeholders {text} {out} {ref}.
    tts_engine: str = "piper"
    tts_speaker_wav: str | None = None      # muestra de referencia para clonar voz
    tts_language: str = "es"
    tts_command: str | None = None          # plantilla para tts_engine="command"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
