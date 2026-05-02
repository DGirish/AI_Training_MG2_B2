from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Stackyon Intelligent Chat")
    environment: str = os.getenv("ENVIRONMENT", os.getenv("LITELLM_ENVIRONMENT", "development"))

    # LiteLLM gateway settings from existing .env
    litellm_proxy_url: str = os.getenv("LITELLM_PROXY_URL", "")
    litellm_api_key: str = os.getenv("LITELLM_API_KEY", os.getenv("LITELLM_VIRTUAL_KEY", ""))
    llm_model: str = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
    litellm_user_id: str | None = os.getenv("LITELLM_USER_ID")
    litellm_department: str | None = os.getenv("LITELLM_DEPARTMENT")

    # Auth & JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # Database - convert to async dialect if needed
    _raw_database_url: str | None = os.getenv("DATABASE_URL")

    @property
    def database_url(self) -> str | None:
        if not self._raw_database_url:
            return None
        # Convert standard PostgreSQL URL to async driver (asyncpg)
        url = self._raw_database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str | None = os.getenv("GOOGLE_REDIRECT_URI")
    chroma_persist_dir: str | None = os.getenv("CHROMA_PERSIST_DIR")
    google_service_account_json: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")

    frontend_origins_raw: str = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    @property
    def frontend_origins(self) -> list[str]:
        origins = [item.strip() for item in self.frontend_origins_raw.split(",") if item.strip()]
        return origins or ["http://localhost:5173"]


settings = Settings()
