"""
Configuration management for the Quotation AI system.
Centralizes all environment variables and application settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""
    
    # Wellx website credentials
    EMAIL: str = os.getenv("EMAIL", "")
    PASSWORD: str = os.getenv("PASSWORD", "")
    
    # AI API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Browserbase Configuration
    BROWSERBASE_API_KEY: str = os.getenv("BROWSERBASE_API_KEY", "")
    BROWSERBASE_PROJECT_ID: str = os.getenv("PROJECT_ID", "")
    
    # Slack Integration
    SLACK_API_KEY: str = os.getenv("SLACK_API_KEY", "")
    SLACK_CHANNEL_NAME = os.getenv("SLACK_CHANNEL_NAME","")
    
    # Microsoft Azure/Graph API Configuration
    TENANT_ID: str = os.getenv("TENANT_ID")
    CLIENT_ID: str = os.getenv("CLIENT_ID")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET")
    
    # Google Cloud Storage Configuration
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "email_attachments_wellx")
    GCS_AUTH_JSON_FILE: str = os.getenv("GCS_AUTH_JSON_FILE", "wellx-ai-staging.json")
    
    # PostgreSQL Database Configuration
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Application Settings
    MAX_CONCURRENT_PROCESSING: int = int(os.getenv("MAX_CONCURRENT_PROCESSING", "3"))
    WEBHOOK_CLIENT_STATE: str = os.getenv("WEBHOOK_CLIENT_STATE", "secure123")
    
    # File Storage Paths
    ATTACHMENTS_DIR: str = "./attachments"
    TEMP_ATTACHMENTS_DIR: str = "./temp_attachments"
    EMAIL_CACHE_DIR: str = "./email_cache"
    
    # File transfer Folder
    DESTINATION_PATH = "TEMP_CENSUS_FILE_PATH"
    
    # Token file path
    TOKEN_FILE: str = "token.json"
    
    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are present."""
        required_settings = [
            "EMAIL", "PASSWORD", "GEMINI_API_KEY", "BROWSERBASE_API_KEY",
            "BROWSERBASE_PROJECT_ID", "DB_USER", "DB_PASSWORD", "DB_NAME"
        ]
        
        missing = []
        for setting in required_settings:
            if not getattr(self, setting):
                missing.append(setting)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True

# Global settings instance
settings = Settings()