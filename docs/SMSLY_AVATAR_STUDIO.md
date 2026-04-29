# SMSLY Avatar Studio

## Overview
SMSLY Avatar is a creator-safe live avatar / IRL skin system. It allows users to upload "Avatar Skins" and apply them to a live camera feed (via static frame transformations) or stream them using an OBS Browser Source. It enforces strict moderation, consent validation, and synthetic watermarking to prevent abuse and impersonation.

## Architecture

### Backend
- **Framework:** FastAPI with SQLAlchemy and SQLite.
- **Models:** `AvatarSkin`, `AvatarSession`, `AvatarRequest`, `AvatarAuditLog`, `AvatarModerationResult`.
- **Uploads:** Handled securely, verified via Pillow, and stored in `data/avatar_uploads`.
- **Auth Layer:** Uses a lightweight `X-SMSLY-User-ID` header for development/demo (controlled by `SMSLY_AVATAR_DEV_AUTH`).
- **Safety & Moderation:** Local rules-based module checking for unsafe prompts, public figure impersonation, and missing consent. Logs every sensitive action to the Audit Log.

### Frontend
- **Framework:** Plain HTML/CSS/JS (Vanilla) loaded via FastAPI's StaticFiles.
- **UI:** A modern, dark, glassmorphism UI matching the reference requirements. Includes a large live preview (`getUserMedia`), skin list, viewer request queue, and settings tab.
- **OBS Integration:** `/static/avatar-obs.html` serves as the browser source. It polls the backend securely using an unguessable overlay token.
- **Mock Fallback:** True real-time AI video is not implemented to avoid extreme lag; instead, the UI supports a "Generate Frame Preview" that pushes a webcam frame to the existing `/api/transform` endpoint.

## Setup Instructions
1. Run the standard app setup or configure the environment manually.
2. Ensure the new environment variables in `.env` (copied from `.env.example`) are set.
3. Start the server using `uvicorn client.main:app --host 0.0.0.0 --port 8000`.
4. Open the UI at `http://localhost:8000/static/avatar.html`.

## Environment Variables
```env
SMSLY_AVATAR_DEV_AUTH=true
SMSLY_AVATAR_DEMO_USER_ID=demo-user
SMSLY_AVATAR_DATABASE_URL=sqlite:///./data/smsly_avatar.db
SMSLY_AVATAR_UPLOAD_DIR=./data/avatar_uploads
SMSLY_AVATAR_MAX_UPLOAD_MB=10
SMSLY_AVATAR_WATERMARK_REQUIRED=true
SMSLY_AVATAR_OVERLAY_BASE_URL=http://localhost:8000/static/avatar-obs.html
SMSLY_AVATAR_MODERATION_PROVIDER=local_rules
SMSLY_AVATAR_ENABLE_PLAYGROUND=true
```

## Known Limitations
- The "Playground" prompt generator is a UI placeholder as no explicit prompt LLM integration is hooked up beyond the basic `/api/transform`.
- True real-time continuous video transformation is deliberately avoided.
- The default SQLite database is not configured for a full production multi-worker deployment; consider migrating to PostgreSQL using Alembic migrations in the future.
