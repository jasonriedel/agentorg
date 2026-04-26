from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str
    github_token: str
    github_repo: str  # "owner/repo"

    database_url: str = "sqlite+aiosqlite:///./agentorg.db"
    souls_dir: str = "../souls"
    workflows_dir: str = "../workflows"
    default_model: str = "claude-sonnet-4-6"
    github_webhook_secret: str = ""  # optional; if set, validates HMAC-SHA256 signatures


settings = Settings()
