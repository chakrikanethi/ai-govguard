from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_ID: str = "ai-govguard-dev"
    DATASET_ID: str = "invoices"
    MODEL_NAME: str = "invoice_anomaly_model"
    USE_MOCK_MODEL: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
