"""Pydantic schemas for API responses"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class MemberResponse(BaseModel):
    """Member response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    guild_id: int
    username: str
    nickname: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[str] = None
    join_datetime: Optional[datetime] = None
    onboarding_status: int
    onboarding_completed_at: Optional[datetime] = None
    last_change_datetime: Optional[datetime] = None
    extra_data: Optional[Dict[str, Any]] = None


class GuildResponse(BaseModel):
    """Guild response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    guild_id: int
    guild_name: str
    is_active: bool
    created_at: datetime
    settings: Dict[str, Any]


class ConfigResponse(BaseModel):
    """Config response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str
    description: Optional[str] = None
    guild_id: int
    updated_at: datetime


class StatsResponse(BaseModel):
    """Statistics response schema"""
    total_guilds: int
    total_members: int
    onboarded_members: int
    pending_members: int


class AuditLogResponse(BaseModel):
    """Audit log response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    guild_id: Optional[int] = None
    user_id: Optional[int] = None
    discord_username: Optional[str] = None
    action: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None