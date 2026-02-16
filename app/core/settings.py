"""
Application settings and configuration management using Pydantic Settings.

This module provides centralized configuration with environment variable loading,
type validation, and default values. All settings are loaded from .env file or
environment variables.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """MongoDB database configuration settings."""
    
    mongodb_connection_string: str = Field(
        ...,
        description="MongoDB Atlas connection string",
        validation_alias="MONGODB_CONNECTION_STRING",
    )
    
    db_name: str = Field(
        default="finhub",
        description="MongoDB database name",
        validation_alias="DB_NAME",
    )
    
    max_pool_size: int = Field(
        default=50,
        description="Maximum MongoDB connection pool size",
        validation_alias="DB_MAX_POOL_SIZE",
    )
    
    min_pool_size: int = Field(
        default=10,
        description="Minimum MongoDB connection pool size",
        validation_alias="DB_MIN_POOL_SIZE",
    )
    
    server_selection_timeout_ms: int = Field(
        default=5000,
        description="MongoDB server selection timeout in milliseconds",
        validation_alias="DB_SERVER_SELECTION_TIMEOUT_MS",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AppSettings(BaseSettings):
    """General application configuration settings."""
    
    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
        validation_alias="ENVIRONMENT",
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        validation_alias="LOG_LEVEL",
    )
    
    app_name: str = Field(
        default="FinHub API",
        description="Application name",
        validation_alias="APP_NAME",
    )
    
    app_version: str = Field(
        default="0.1.0",
        description="Application version",
        validation_alias="APP_VERSION",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AzureSettings(BaseSettings):
    """Azure infrastructure configuration settings."""
    
    subscription_id: str | None = Field(
        default=None,
        description="Azure subscription ID",
        validation_alias="AZURE_SUBSCRIPTION_ID",
    )
    
    resource_group: str | None = Field(
        default=None,
        description="Azure resource group name",
        validation_alias="AZURE_RESOURCE_GROUP",
    )
    
    container_app_name: str | None = Field(
        default=None,
        description="Azure Container App name",
        validation_alias="AZURE_CONTAINER_APP_NAME",
    )
    
    environment_name: str | None = Field(
        default=None,
        description="Azure Container App Environment name",
        validation_alias="AZURE_ENVIRONMENT",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class EmailSettings(BaseSettings):
    """Email service configuration settings (for future use)."""
    
    smtp_host: str | None = Field(
        default=None,
        description="SMTP server host",
        validation_alias="EMAIL_SMTP_HOST",
    )
    
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
        validation_alias="EMAIL_SMTP_PORT",
    )
    
    smtp_user: str | None = Field(
        default=None,
        description="SMTP username",
        validation_alias="EMAIL_SMTP_USER",
    )
    
    smtp_password: str | None = Field(
        default=None,
        description="SMTP password",
        validation_alias="EMAIL_SMTP_PASSWORD",
    )
    
    from_email: str | None = Field(
        default=None,
        description="Default sender email address",
        validation_alias="EMAIL_FROM",
    )
    
    from_name: str | None = Field(
        default=None,
        description="Default sender name",
        validation_alias="EMAIL_FROM_NAME",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AuthSettings(BaseSettings):
    """Authentication and authorization configuration settings (for future use)."""
    
    secret_key: str | None = Field(
        default=None,
        description="Secret key for JWT token signing",
        validation_alias="AUTH_SECRET_KEY",
    )
    
    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
        validation_alias="AUTH_ALGORITHM",
    )
    
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
        validation_alias="AUTH_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days",
        validation_alias="AUTH_REFRESH_TOKEN_EXPIRE_DAYS",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class Settings(BaseSettings):
    """
    Main application settings with nested configuration sections.
    
    Settings are loaded from environment variables or .env file.
    Each section is organized by domain (database, app, azure, email, auth).
    """
    
    # Database configuration
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    
    # Application configuration
    app: AppSettings = Field(default_factory=AppSettings)
    
    # Azure configuration
    azure: AzureSettings = Field(default_factory=AzureSettings)
    
    # Email configuration (for future use)
    email: EmailSettings = Field(default_factory=EmailSettings)
    
    # Authentication configuration (for future use)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
        env_nested_delimiter="__",  # Support nested config via ENV_VAR__NESTED
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get the application settings singleton.
    
    Loads settings from .env file and environment variables on first call.
    Subsequent calls return the cached instance.
    
    Returns:
        Settings: Application settings instance
        
    Raises:
        ValidationError: If required settings are missing or invalid
    """
    global _settings
    
    if _settings is None:
        _settings = Settings()
    
    return _settings


# Convenience function for direct access
settings = get_settings()
