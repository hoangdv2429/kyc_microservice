from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "EchoFi KYC Service"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str | None = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, any]) -> any:
        if isinstance(v, str):
            return v
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

    # RabbitMQ
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str

    # MinIO/S3
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "kyc-documents"
    MINIO_SECURE: bool = True

    # OCR Settings
    TESSERACT_CMD: str = "tesseract"
    OCR_LANGUAGES: List[str] = ["eng", "vie", "chi_sim"]

    # Face Matching
    FACE_MATCH_THRESHOLD: float = 0.7
    LIVENESS_THRESHOLD: float = 0.8

    # Email Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    FROM_EMAIL: str = ""

    # Telegram Settings
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    # KYC Settings
    AUTO_APPROVAL_THRESHOLD: float = 0.85
    MANUAL_REVIEW_THRESHOLD: float = 0.65
    KYC_DATA_RETENTION_DAYS: int = 1825  # 5 years
    
    # Smart Contract Integration
    BLOCKCHAIN_RPC_URL: str = ""
    CONTRACT_ADDRESS: str = ""
    CONTRACT_PRIVATE_KEY: str = ""
    
    # Security & Compliance
    AES_ENCRYPTION_KEY: str = ""
    GDPR_AUTO_DELETE_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # 7 years
    
    # Performance Settings
    MAX_REQUESTS_PER_DAY: int = 1000
    OCR_TIMEOUT_SECONDS: int = 30
    FACE_MATCH_TIMEOUT_SECONDS: int = 15

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "allow"  # Allow extra fields in the .env file
    }

settings = Settings()