import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from avatar_db import get_db
from avatar_models import AvatarSkin, AvatarSession, AvatarRequest, AvatarAuditLog, AvatarModerationResult
from avatar_schemas import (
    AvatarSkinResponse, AvatarSkinCreate, AvatarSessionResponse,
    AvatarSessionCreate, AvatarRequestResponse, AvatarRequestCreate,
    AvatarAuditLogResponse, AvatarModerationResultResponse
)
from avatar_auth import get_current_avatar_user
from avatar_storage import save_avatar_upload
from avatar_moderation import moderate_avatar_upload, moderate_avatar_prompt, create_moderation_result
import os
from io import BytesIO
from PIL import Image
from ai_pipeline import get_transformer
import time
from pydantic import BaseModel
import httpx

router = APIRouter()

def log_audit(db: Session, user_id: str, action: str, entity_type: str, entity_id: str, metadata: dict = None):
    log = AvatarAuditLog(
        id=uuid.uuid4().hex,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata
    )
    db.add(log)
    db.commit()

# --- SKINS ---

@router.get("/api/avatar/skins", response_model=List[AvatarSkinResponse])
def get_skins(db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    skins = db.query(AvatarSkin).filter(AvatarSkin.user_id == current_user, AvatarSkin.deleted_at == None).all()
    return skins

@router.post("/api/avatar/skins", response_model=AvatarSkinResponse)
async def create_skin(
    name: str = Form(...),
    source_type: str = Form(...),
    consent_status: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_avatar_user)
):
    # Process Upload
    file_path, url = await save_avatar_upload(file)

    # Moderate Upload
    status, reason = moderate_avatar_upload({"name": name, "consent_status": consent_status}, current_user)

    skin_id = uuid.uuid4().hex

    skin = AvatarSkin(
        id=skin_id,
        user_id=current_user,
        name=name,
        source_type=source_type,
        consent_status=consent_status,
        source_image_url=url,
        moderation_status=status
    )

    db.add(skin)

    # Save Moderation Result
    mod_res = AvatarModerationResult(**create_moderation_result("skin", skin_id, status, reason))
    db.add(mod_res)

    log_audit(db, current_user, "create_skin", "skin", skin_id, {"status": status, "reason": reason})
    db.commit()
    db.refresh(skin)

    return skin

@router.patch("/api/avatar/skins/{id}", response_model=AvatarSkinResponse)
def update_skin(id: str, active: Optional[bool] = Form(None), db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    skin = db.query(AvatarSkin).filter(AvatarSkin.id == id, AvatarSkin.user_id == current_user).first()
    if not skin:
        raise HTTPException(status_code=404, detail="Skin not found.")

    if active is not None:
        skin.active = active

    db.commit()
    db.refresh(skin)
    return skin

@router.delete("/api/avatar/skins/{id}")
def delete_skin(id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    skin = db.query(AvatarSkin).filter(AvatarSkin.id == id, AvatarSkin.user_id == current_user).first()
    if not skin:
        raise HTTPException(status_code=404, detail="Skin not found.")

    from datetime import datetime, timezone
    skin.deleted_at = datetime.now(timezone.utc)
    log_audit(db, current_user, "delete_skin", "skin", id)
    db.commit()
    return {"ok": True}

@router.post("/api/avatar/skins/{id}/activate")
def activate_skin(id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    skin = db.query(AvatarSkin).filter(AvatarSkin.id == id, AvatarSkin.user_id == current_user).first()
    if not skin:
        raise HTTPException(status_code=404, detail="Skin not found.")

    if skin.moderation_status != "approved" or skin.consent_status != "confirmed":
        raise HTTPException(status_code=400, detail="Skin must be approved and consent confirmed before activation.")

    # Deactivate others
    db.query(AvatarSkin).filter(AvatarSkin.user_id == current_user, AvatarSkin.id != id).update({"active": False})
    skin.active = True

    # Update Session if exists
    session = db.query(AvatarSession).filter(AvatarSession.user_id == current_user).first()
    if session:
        session.active_skin_id = id

    log_audit(db, current_user, "activate_skin", "skin", id)
    db.commit()
    return {"ok": True, "skin_id": id}

@router.post("/api/avatar/skins/{id}/revoke-consent")
def revoke_consent(id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    skin = db.query(AvatarSkin).filter(AvatarSkin.id == id, AvatarSkin.user_id == current_user).first()
    if not skin:
        raise HTTPException(status_code=404, detail="Skin not found.")

    skin.consent_status = "revoked"
    skin.active = False
    log_audit(db, current_user, "revoke_consent", "skin", id)
    db.commit()
    return {"ok": True}

@router.post("/api/avatar/skins/{id}/generate-preview")
async def generate_preview(
    id: str,
    file: UploadFile = File(...),
    prompt: str = Form(...),
    strength: float = Form(0.6),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_avatar_user)
):
    # Confirm skin ownership
    skin = db.query(AvatarSkin).filter(AvatarSkin.id == id, AvatarSkin.user_id == current_user).first()
    if not skin:
        raise HTTPException(status_code=404, detail="Skin not found.")

    # Confirm skin consent
    if skin.consent_status != "confirmed":
        raise HTTPException(status_code=400, detail="Skin consent must be confirmed.")

    # Confirm moderation
    if skin.moderation_status != "approved":
        raise HTTPException(status_code=400, detail="Skin must be approved.")

    # Prompt safety check
    status, reason = moderate_avatar_prompt(prompt, current_user)
    if status != "approved":
        raise HTTPException(status_code=400, detail=f"Prompt rejected: {reason}")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        # Read the uploaded image
        image_bytes = await file.read()
        init_image = Image.open(BytesIO(image_bytes))

        # Get the AI transformer
        transformer = get_transformer()

        # Transform the image
        start_time = time.time()
        try:
            result_image = transformer.transform_image(init_image, prompt, strength=strength)
        except Exception as e:
            if str(e) == "AVATAR_GENERATION_BUSY":
                raise HTTPException(status_code=429, detail="Avatar generation is already running. Please try again in a moment.")
            raise e
        generation_time = time.time() - start_time

        # Save output into data/avatar_uploads/processed/
        avatar_upload_dir = os.environ.get("SMSLY_AVATAR_UPLOAD_DIR", "./data/avatar_uploads")
        processed_dir = os.path.join(avatar_upload_dir, "processed")
        os.makedirs(processed_dir, exist_ok=True)

        filename = f"processed_{uuid.uuid4().hex}_{int(time.time())}.jpg"
        filepath = os.path.join(processed_dir, filename)

        result_image.save(filepath, format="JPEG", quality=90)
        processed_asset_url = f"/avatar-media/processed/{filename}"

        # Update AvatarSkin.processed_asset_url
        skin.processed_asset_url = processed_asset_url

        # Write AvatarAuditLog action="generate_preview"
        log_audit(db, current_user, "generate_preview", "skin", id, {"prompt": prompt, "strength": strength, "asset_url": processed_asset_url})

        db.commit()
        db.refresh(skin)

        session = db.query(AvatarSession).filter(AvatarSession.user_id == current_user).first()

        return {
            "skin": AvatarSkinResponse.model_validate(skin).model_dump(),
            "session": AvatarSessionResponse.model_validate(session).model_dump() if session else None,
            "performance": {
                "device": get_transformer().device,
                "generation_time": round(generation_time, 2)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- SESSIONS ---

@router.get("/api/avatar/session", response_model=Optional[AvatarSessionResponse])
def get_session(db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    return db.query(AvatarSession).filter(AvatarSession.user_id == current_user).first()

@router.post("/api/avatar/session/start", response_model=AvatarSessionResponse)
def start_session(data: AvatarSessionCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    session = db.query(AvatarSession).filter(AvatarSession.user_id == current_user).first()

    if not session:
        session = AvatarSession(
            id=uuid.uuid4().hex,
            user_id=current_user,
            overlay_token=uuid.uuid4().hex,
            source_type=data.source_type,
            duration_seconds=data.duration_seconds,
            status="live"
        )
        db.add(session)
    else:
        session.status = "live"
        session.source_type = data.source_type
        session.duration_seconds = data.duration_seconds

    log_audit(db, current_user, "start_session", "session", session.id)
    db.commit()
    db.refresh(session)
    return session

@router.post("/api/avatar/session/stop")
def stop_session(db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    session = db.query(AvatarSession).filter(AvatarSession.user_id == current_user).first()
    if session:
        session.status = "stopped"
        log_audit(db, current_user, "stop_session", "session", session.id)
        db.commit()
    return {"ok": True}


# --- REQUESTS ---

@router.get("/api/avatar/requests", response_model=List[AvatarRequestResponse])
def get_requests(db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    session = db.query(AvatarSession).filter(AvatarSession.user_id == current_user).first()
    if not session:
        return []
    return db.query(AvatarRequest).filter(AvatarRequest.session_id == session.id).all()

@router.post("/api/avatar/requests", response_model=AvatarRequestResponse)
def create_request(data: AvatarRequestCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    # Validate prompt
    status, reason = moderate_avatar_prompt(data.prompt or "", current_user)

    req_id = uuid.uuid4().hex
    req = AvatarRequest(
        id=req_id,
        session_id=data.session_id,
        requester_name=data.requester_name,
        requester_handle=data.requester_handle,
        prompt=data.prompt,
        status="waiting_mod" if status == "approved" else "rejected",
        moderation_reason=reason
    )
    db.add(req)

    mod_res = AvatarModerationResult(**create_moderation_result("request", req_id, status, reason))
    db.add(mod_res)

    log_audit(db, current_user, "create_request", "request", req_id)
    db.commit()
    db.refresh(req)
    return req

@router.post("/api/avatar/requests/{id}/approve")
def approve_request(id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    req = db.query(AvatarRequest).join(AvatarSession, AvatarRequest.session_id == AvatarSession.id).filter(AvatarRequest.id == id, AvatarSession.user_id == current_user).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found or unauthorized.")
    req.status = "approved"
    log_audit(db, current_user, "approve_request", "request", id)
    db.commit()
    return {"ok": True}

@router.post("/api/avatar/requests/{id}/reject")
def reject_request(id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    req = db.query(AvatarRequest).join(AvatarSession, AvatarRequest.session_id == AvatarSession.id).filter(AvatarRequest.id == id, AvatarSession.user_id == current_user).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found or unauthorized.")
    req.status = "rejected"
    log_audit(db, current_user, "reject_request", "request", id)
    db.commit()
    return {"ok": True}

@router.post("/api/avatar/requests/{id}/apply")
def apply_request(id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    req = db.query(AvatarRequest).join(AvatarSession, AvatarRequest.session_id == AvatarSession.id).filter(AvatarRequest.id == id, AvatarSession.user_id == current_user).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found or unauthorized.")

    req.status = "playing"
    db.query(AvatarRequest).filter(AvatarRequest.session_id == req.session_id, AvatarRequest.id != id, AvatarRequest.status == "playing").update({"status": "completed"})

    log_audit(db, current_user, "apply_request", "request", id)
    db.commit()
    return {"ok": True}

# --- OBS / BROWSER SOURCE ---

@router.get("/api/avatar/obs-source/{token}")
def get_obs_source(token: str, db: Session = Depends(get_db)):
    session = db.query(AvatarSession).filter(AvatarSession.overlay_token == token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid token")

    skin = None
    if session.active_skin_id:
        skin = db.query(AvatarSkin).filter(AvatarSkin.id == session.active_skin_id).first()

    return {
        "status": session.status,
        "watermark_enabled": session.watermark_enabled,
        "active_skin": {
            "name": skin.name,
            "processed_asset_url": skin.processed_asset_url,
            "source_image_url": skin.source_image_url
        } if skin else None
    }

@router.post("/api/avatar/obs-source/regenerate-token")
def regenerate_token(db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    session = db.query(AvatarSession).filter(AvatarSession.user_id == current_user).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.overlay_token = uuid.uuid4().hex
    log_audit(db, current_user, "regenerate_token", "session", session.id)
    db.commit()
    return {"ok": True, "token": session.overlay_token}

# --- OPENROUTER / PROMPTS ---

class PromptGenerateRequest(BaseModel):
    idea: str
    style: Optional[str] = "cinematic"
    negative_prompt: Optional[str] = ""
    model: Optional[str] = "openai/gpt-4o-mini"
    openrouter_api_key: Optional[str] = None

@router.post("/api/avatar/prompts/generate")
async def generate_prompt(req: PromptGenerateRequest, current_user: str = Depends(get_current_avatar_user)):
    # 1. Local Safety Check
    status, reason = moderate_avatar_prompt(req.idea, current_user)
    if status != "approved":
        raise HTTPException(status_code=400, detail=f"Idea rejected: {reason}")

    # 2. Get API Key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    allow_browser = os.environ.get("SMSLY_AVATAR_ALLOW_BROWSER_OPENROUTER_KEY", "true").lower() == "true"

    if allow_browser and req.openrouter_api_key:
        api_key = req.openrouter_api_key

    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured")

    model_to_use = req.model or os.environ.get("SMSLY_AVATAR_PROMPT_MODEL", "openai/gpt-4o-mini")

    system_prompt = "You generate safe, original SMSLY Avatar style prompts for synthetic creator avatars. Do not imitate or reference real public figures, celebrities, politicians, private people, or named individuals. Do not create deepfake, deception, or identity-cloning prompts. Create original avatar style descriptions suitable for consent-based image transformation. Keep prompts concise, visual, and production-ready. Always include a watermark/synthetic framing description if relevant. Only return the actual prompt string, do not output conversational text."

    user_prompt = f"Idea: {req.idea}\nStyle: {req.style}"

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://smsly.ai",
                    "X-Title": "SMSLY Avatar"
                },
                json={
                    "model": model_to_use,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                },
                timeout=15.0
            )
            res.raise_for_status()
            data = res.json()

            generated_prompt = data["choices"][0]["message"]["content"].strip()

            # Post-generation local moderation check
            status2, reason2 = moderate_avatar_prompt(generated_prompt, current_user)
            if status2 != "approved":
                 raise HTTPException(status_code=400, detail=f"Generated prompt rejected by safety layer: {reason2}")

            return {
                "ok": True,
                "prompt": generated_prompt,
                "negative_prompt": req.negative_prompt,
                "safety_notes": ["Cleared local safety checks"]
            }
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"OpenRouter API error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt generation failed: {str(e)}")

# --- AUDIT LOGS ---

@router.get("/api/avatar/audit-logs", response_model=List[AvatarAuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db), current_user: str = Depends(get_current_avatar_user)):
    return db.query(AvatarAuditLog).filter(AvatarAuditLog.user_id == current_user).order_by(AvatarAuditLog.created_at.desc()).all()
