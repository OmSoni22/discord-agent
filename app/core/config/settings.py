from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str
    debug: bool

    database_url: str


    log_level: str
    log_dir: str

    class Config:
        env_file = ".env"

settings = Settings()
