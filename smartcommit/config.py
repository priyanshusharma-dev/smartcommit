from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    default_model: str = "llama3.2"
    use_emoji: bool = False
    max_length: int = 72

    class Config:
        env_prefix = "COMMITGEN_"

settings = Settings()