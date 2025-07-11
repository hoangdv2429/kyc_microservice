from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )
    
    PROJECT_NAME: str = "KYC Service"
    API_V1_STR: str = "/api/v1"
    
    # CORS - Fix the type and validator
    CORS_ORIGINS: List[str] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str | None = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, values):
        if isinstance(v, str):
            return v
        # In Pydantic v2, we need to handle this differently
        if hasattr(values, 'data'):
            values_dict = values.data
        else:
            values_dict = values
        return f"postgresql://{values_dict.get('POSTGRES_USER')}:{values_dict.get('POSTGRES_PASSWORD')}@{values_dict.get('POSTGRES_SERVER')}/{values_dict.get('POSTGRES_DB')}"

    # RabbitMQ
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # MinIO/S3
    MINIO_INTERNAL_ENDPOINT: str = "minio:9000"  # For backend-to-MinIO communication
    MINIO_EXTERNAL_ENDPOINT: str = "localhost:9000"  # For frontend-to-MinIO communication
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "kyc-documents"
    MINIO_SECURE: bool = False
    
    @property
    def internal_minio_endpoint(self) -> str:
        """Get the internal MinIO endpoint for backend operations"""
        return self.MINIO_INTERNAL_ENDPOINT
    
    @property
    def external_minio_endpoint(self) -> str:
        """Get the external MinIO endpoint for frontend operations"""
        return self.MINIO_EXTERNAL_ENDPOINT

    # OCR Settings
    TESSERACT_CMD: str = "tesseract"
    OCR_LANGUAGES: List[str] = ["eng", "vie", "chi_sim"]

    # Face Matching
    FACE_MATCH_THRESHOLD: float = 0.7
    LIVENESS_THRESHOLD: float = 0.8

    # Email Settings (made optional)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    FROM_EMAIL: str = ""

    # Telegram Settings (made optional)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    # KYC Settings
    AUTO_APPROVAL_THRESHOLD: float = 0.85
    MANUAL_REVIEW_THRESHOLD: float = 0.65
    KYC_DATA_RETENTION_DAYS: int = 1825  # 5 years
    
    # Smart Contract Integration (made optional)
    BLOCKCHAIN_RPC_URL: str = ""
    CONTRACT_ADDRESS: str = ""
    CONTRACT_PRIVATE_KEY: str = ""
    
    # Security & Compliance (made optional)
    AES_ENCRYPTION_KEY: str = ""
    GDPR_AUTO_DELETE_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # 7 years
    
    # Performance Settings
    MAX_REQUESTS_PER_DAY: int = 1000
    OCR_TIMEOUT_SECONDS: int = 30
    FACE_MATCH_TIMEOUT_SECONDS: int = 15

settings = Settings()