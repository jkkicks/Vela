"""SQLModel database models for Vela"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, JSON, Column, Relationship
from sqlalchemy import UniqueConstraint, BigInteger
import sqlalchemy as sa


class Guild(SQLModel, table=True):
    """Support for multi-guild architecture from the start"""

    __tablename__ = "guilds"

    id: Optional[int] = Field(default=None, primary_key=True)
    guild_id: int = Field(index=True, unique=True, sa_column=Column(BigInteger))
    guild_name: str
    bot_token: str  # Encrypted - allows different bots per guild
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    settings: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    configs: list["Config"] = Relationship(back_populates="guild")
    channels: list["Channel"] = Relationship(back_populates="guild")
    roles: list["Role"] = Relationship(back_populates="guild")
    members: list["Member"] = Relationship(back_populates="guild")
    admin_users: list["AdminUser"] = Relationship(back_populates="guild")


class Config(SQLModel, table=True):
    """Per-guild configuration"""

    __tablename__ = "configs"
    __table_args__ = (UniqueConstraint("key", "guild_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True)
    guild_id: int = Field(foreign_key="guilds.guild_id", sa_column=Column(BigInteger))
    value: str
    description: Optional[str] = None
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(sa.DateTime, onupdate=datetime.utcnow),
    )

    # Relationships
    guild: Optional[Guild] = Relationship(back_populates="configs")


class AdminUser(SQLModel, table=True):
    """Web UI administrators - Discord users with admin access"""

    __tablename__ = "admin_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    discord_id: int = Field(index=True, unique=True, sa_column=Column(BigInteger))
    discord_username: str
    guild_id: int = Field(foreign_key="guilds.guild_id", sa_column=Column(BigInteger))
    is_super_admin: bool = False  # Can manage all guilds
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    # Relationships
    guild: Optional[Guild] = Relationship(back_populates="admin_users")


class Channel(SQLModel, table=True):
    """Discord channels configuration"""

    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("channel_id", "guild_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, sa_column=Column(BigInteger))
    channel_type: str  # 'welcome', 'bot_commands', 'logs'
    guild_id: int = Field(foreign_key="guilds.guild_id", sa_column=Column(BigInteger))
    name: Optional[str] = None
    enabled: bool = True
    message_id: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger)
    )  # For welcome channel: ID of the welcome message

    # Relationships
    guild: Optional[Guild] = Relationship(back_populates="channels")


class Role(SQLModel, table=True):
    """Discord roles configuration"""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("role_id", "guild_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(index=True, sa_column=Column(BigInteger))
    role_name: str
    role_type: Optional[str] = None  # 'onboarded', 'admin'
    permissions: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    guild_id: int = Field(foreign_key="guilds.guild_id", sa_column=Column(BigInteger))

    # Relationships
    guild: Optional[Guild] = Relationship(back_populates="roles")


class Member(SQLModel, table=True):
    """Per-guild member data"""

    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("user_id", "guild_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, sa_column=Column(BigInteger))
    guild_id: int = Field(foreign_key="guilds.guild_id", sa_column=Column(BigInteger))
    username: str
    nickname: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[str] = None
    join_datetime: Optional[datetime] = None
    onboarding_status: int = 0
    onboarding_completed_at: Optional[datetime] = None
    last_change_datetime: Optional[datetime] = None
    extra_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSON)
    )  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    # Relationships
    guild: Optional[Guild] = Relationship(back_populates="members")


class AuditLog(SQLModel, table=True):
    """Audit log for tracking all actions"""

    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    guild_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    user_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    discord_username: Optional[str] = None
    action: str
    details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    ip_address: Optional[str] = None
