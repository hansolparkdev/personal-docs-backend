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

    rag_similarity_threshold: float = 0.75  # 코사인 거리 임계값 (0에 가까울수록 유사)
    max_upload_size_bytes: int = 52428800  # 50MB
    allowed_extensions: set[str] = {
        # 문서
        ".pdf", ".docx", ".doc", ".rtf", ".odt",
        # 프레젠테이션
        ".pptx", ".ppt",
        # 스프레드시트
        ".xlsx", ".xls", ".csv",
        # 텍스트
        ".txt", ".md", ".markdown",
        # 웹
        ".html", ".htm",
        # 이메일
        ".eml", ".msg",
        # 코드/데이터
        ".json", ".xml", ".yaml", ".yml",
        # 이미지 (MarkItDown OCR 지원)
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    }


settings = Settings()
