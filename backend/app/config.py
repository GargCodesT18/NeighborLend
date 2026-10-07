from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR/".env", extra="ignore")

    database_url: str = "sqlite:///./neighborlend.db"
    jwt_secret: str = "neighborlend-super-secret-key-2026-prototype"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    upload_dir: str = "./uploads"
    public_base_url: str = "http://localhost:8000"
    ai_model_path: str = "./ai_service/best_model/best.pt"
    ai_confidence_threshold: float = 0.45
    mock_payments: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
    admin_emails: str = "admin@neighborlend.com"
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
