from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_docs"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "personal-docs"
    minio_secure: bool = False

    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "personal-docs"
    keycloak_client_id: str = "backend"
    keycloak_client_secret: str = ""
    keycloak_jwks_cache_ttl: int = 600
    keycloak_admin_client_id: str = "backend"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    max_upload_size_bytes: int = 52428800  # 50MB
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/markdown",
        "text/x-markdown",
        "text/plain",
        "application/octet-stream",  # 브라우저가 MIME 감지 실패 시
    ]


settings = Settings()
