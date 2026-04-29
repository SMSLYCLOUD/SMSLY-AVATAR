from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime

class AvatarSkinBase(BaseModel):
    name: str
    source_type: str
    watermark_required: Optional[bool] = True
    active: Optional[bool] = False
    consent_status: Optional[str] = "pending"

class AvatarSkinCreate(BaseModel):
    name: str
    source_type: str
    consent_status: str

class AvatarSkinResponse(AvatarSkinBase):
    id: str
    user_id: str
    project_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    source_image_url: Optional[str] = None
    processed_asset_url: Optional[str] = None
    moderation_status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AvatarSessionBase(BaseModel):
    status: str
    source_type: str
    active_skin_id: Optional[str] = None
    watermark_enabled: Optional[bool] = True
    duration_seconds: Optional[int] = None

class AvatarSessionCreate(BaseModel):
    source_type: str
    duration_seconds: Optional[int] = None

class AvatarSessionResponse(AvatarSessionBase):
    id: str
    user_id: str
    overlay_token: str
    browser_source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AvatarRequestBase(BaseModel):
    requester_name: str
    requester_handle: Optional[str] = None
    prompt: Optional[str] = None
    requested_skin_id: Optional[str] = None
    duration_seconds: Optional[int] = None

class AvatarRequestCreate(AvatarRequestBase):
    session_id: str

class AvatarRequestResponse(AvatarRequestBase):
    id: str
    session_id: str
    status: str
    moderation_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AvatarAuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AvatarModerationResultResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    provider: str
    status: str
    confidence: Optional[int] = None
    categories: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
