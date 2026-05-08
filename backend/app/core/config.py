from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


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
    image_gen_model: str = os.getenv("IMAGE_GEN_MODEL", "gemini/imagen-4.0-fast-generate-001")
    litellm_embedding_model: str = os.getenv("LITELLM_EMBEDDING_MODEL", "text-embedding-3-large")
    litellm_user_id: str | None = os.getenv("LITELLM_USER_ID")
    litellm_department: str | None = os.getenv("LITELLM_DEPARTMENT")

    # Auth & JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # Database
    _raw_database_url: str | None = os.getenv("DATABASE_URL")
    database_pooler_url: str | None = os.getenv("DATABASE_POOLER_URL")
    db_connect_timeout_seconds: float = float(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "15"))
    db_command_timeout_seconds: float = float(os.getenv("DB_COMMAND_TIMEOUT_SECONDS", "30"))
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    db_pool_timeout_seconds: float = float(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30"))
    db_pool_recycle_seconds: int = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800"))
    db_connect_retries: int = int(os.getenv("DB_CONNECT_RETRIES", "3"))
    db_connect_retry_backoff_seconds: float = float(os.getenv("DB_CONNECT_RETRY_BACKOFF_SECONDS", "1.5"))

    @staticmethod
    def _to_asyncpg_url(url: str) -> str:
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def database_url(self) -> str | None:
        base_url = self.database_pooler_url or self._raw_database_url
        if not base_url:
            return None

        url = self._to_asyncpg_url(base_url)
        if "pooler.supabase.com" not in url and ".pooler." not in url:
            raise RuntimeError(
                "DATABASE_URL must use a Supabase pooler endpoint. Set DATABASE_POOLER_URL to your pooler connection string."
            )

        return url
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str | None = os.getenv("GOOGLE_REDIRECT_URI")
    chroma_persist_dir: str | None = os.getenv("CHROMA_PERSIST_DIR")
    google_service_account_json: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "chat-assets")

    frontend_origins_raw: str = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    @property
    def frontend_origins(self) -> list[str]:
        origins = [item.strip() for item in self.frontend_origins_raw.split(",") if item.strip()]
        return origins or ["http://localhost:5173"]

    @property
    def resolved_supabase_url(self) -> str | None:
        if self.supabase_url:
            return self.supabase_url

        base_url = self.database_pooler_url or self._raw_database_url
        if not base_url:
            return None

        parsed = urlparse(base_url)
        host = parsed.hostname or ""
        if not host:
            return None

        if host.endswith(".pooler.supabase.com"):
            project_id = host.split(".")[0]
            return f"https://{project_id}.supabase.co"

        if host.endswith(".supabase.co"):
            host_parts = host.split(".")
            if host_parts[0] == "db" and len(host_parts) >= 4:
                return f"https://{host_parts[1]}.supabase.co"
            return f"https://{host}"

        return None

settings = Settings()
