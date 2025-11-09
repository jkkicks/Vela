"""Configuration management module"""
import os
from typing import Optional, Any
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet
import json
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = "sqlite:///./vela.db"

    # Discord OAuth
    discord_client_id: Optional[str] = None
    discord_client_secret: Optional[str] = None
    discord_redirect_uri: str = "http://localhost:8000/auth/callback"

    # API Settings
    api_secret_key: str = "change-this-secret-key-in-production"
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    # Bot Settings (initial values, then managed via DB)
    bot_token: Optional[str] = None
    guild_id: Optional[int] = None

    # Security
    encryption_key: Optional[str] = None

    # Logging
    debug: bool = False
    log_level: str = "INFO"

    # Redis (optional)
    redis_url: Optional[str] = None

    # CORS - as a string, will be split by comma
    cors_origins_str: str = "http://localhost:3000,http://localhost:8000"

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from string"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env


# Create settings instance
settings = Settings()

# Initialize encryption
if not settings.encryption_key:
    # Generate a new encryption key if not provided
    settings.encryption_key = Fernet.generate_key().decode()
    logger.warning("Generated new encryption key. Save this in .env for persistence.")

fernet = Fernet(settings.encryption_key.encode() if isinstance(settings.encryption_key, str) else settings.encryption_key)


def encrypt_value(value: str) -> str:
    """Encrypt a string value"""
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value"""
    return fernet.decrypt(encrypted_value.encode()).decode()


def get_config_from_db(key: str, guild_id: int) -> Optional[str]:
    """Get configuration value from database"""
    from src.shared.database import get_session
    from src.shared.models import Config
    from sqlmodel import select

    with next(get_session()) as session:
        config = session.exec(
            select(Config).where(
                Config.key == key,
                Config.guild_id == guild_id
            )
        ).first()

        return config.value if config else None


def set_config_in_db(key: str, value: str, guild_id: int, description: Optional[str] = None):
    """Set configuration value in database"""
    from src.shared.database import get_session
    from src.shared.models import Config
    from sqlmodel import select
    from datetime import datetime

    with next(get_session()) as session:
        config = session.exec(
            select(Config).where(
                Config.key == key,
                Config.guild_id == guild_id
            )
        ).first()

        if config:
            config.value = value
            config.updated_at = datetime.utcnow()
            if description:
                config.description = description
        else:
            config = Config(
                key=key,
                value=value,
                guild_id=guild_id,
                description=description
            )
            session.add(config)

        session.commit()
        logger.info(f"Configuration updated: {key} for guild {guild_id}")


def get_guild_settings(guild_id: int) -> dict:
    """Get all settings for a guild"""
    from src.shared.database import get_session
    from src.shared.models import Guild, Config, Channel, Role
    from sqlmodel import select

    with next(get_session()) as session:
        # Get guild info
        guild = session.exec(
            select(Guild).where(Guild.guild_id == guild_id)
        ).first()

        if not guild:
            return {}

        # Get all configs
        configs = session.exec(
            select(Config).where(Config.guild_id == guild_id)
        ).all()

        # Get all channels
        channels = session.exec(
            select(Channel).where(Channel.guild_id == guild_id)
        ).all()

        # Get all roles
        roles = session.exec(
            select(Role).where(Role.guild_id == guild_id)
        ).all()

        return {
            "guild": {
                "id": guild.guild_id,
                "name": guild.guild_name,
                "is_active": guild.is_active,
                "settings": guild.settings
            },
            "configs": {c.key: c.value for c in configs},
            "channels": {c.channel_type: {
                "id": c.channel_id,
                "name": c.name,
                "enabled": c.enabled
            } for c in channels},
            "roles": {r.role_type: {
                "id": r.role_id,
                "name": r.role_name,
                "permissions": r.permissions
            } for r in roles if r.role_type}
        }