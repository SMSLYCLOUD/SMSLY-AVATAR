from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.sql import func
from avatar_db import Base

class AvatarSkin(Base):
    __tablename__ = "avatar_skins"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    project_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    source_image_url = Column(String, nullable=True)
    processed_asset_url = Column(String, nullable=True)
    source_type = Column(String, nullable=False) # upload | generated | imported | synthetic_demo
    consent_status = Column(String, nullable=False, default="pending") # pending | confirmed | rejected | revoked
    moderation_status = Column(String, nullable=False, default="pending") # pending | approved | rejected | flagged
    watermark_required = Column(Boolean, default=True)
    active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class AvatarSession(Base):
    __tablename__ = "avatar_sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False, default="idle") # idle | live | paused | stopped | error
    active_skin_id = Column(String, nullable=True)
    source_type = Column(String, nullable=False) # webcam | browser | upload | obs
    overlay_token = Column(String, unique=True, index=True, nullable=False)
    browser_source_url = Column(String, nullable=True)
    watermark_enabled = Column(Boolean, default=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AvatarRequest(Base):
    __tablename__ = "avatar_requests"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    requester_name = Column(String, nullable=False)
    requester_handle = Column(String, nullable=True)
    prompt = Column(String, nullable=True)
    requested_skin_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="waiting_mod") # waiting_mod | approved | rejected | ready | playing | completed | failed
    moderation_reason = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AvatarAuditLog(Base):
    __tablename__ = "avatar_audit_logs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AvatarModerationResult(Base):
    __tablename__ = "avatar_moderation_results"

    id = Column(String, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    status = Column(String, nullable=False)
    confidence = Column(Integer, nullable=True)
    categories = Column(JSON, nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
