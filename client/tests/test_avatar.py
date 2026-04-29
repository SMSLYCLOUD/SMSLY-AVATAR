import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PIL import Image

from client.main import app
from client.avatar_db import Base, get_db
from client.avatar_moderation import detect_impersonation_terms

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_smsly_avatar.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Helper headers
headers = {"X-SMSLY-User-ID": "test-user-1"}

def create_valid_image_bytes():
    import io
    file = io.BytesIO()
    image = Image.new("RGB", (100, 100), color="red")
    image.save(file, "png")
    file.seek(0)
    return file

def test_get_skins_empty():
    response = client.get("/api/avatar/skins", headers=headers)
    assert response.status_code == 200

def test_create_skin_rejected_consent():
    file = create_valid_image_bytes()

    response = client.post(
        "/api/avatar/skins",
        headers=headers,
        data={
            "name": "My Cool Skin",
            "source_type": "upload",
            "consent_status": "pending"
        },
        files={"file": ("test.png", file, "image/png")}
    )
    # the upload works, but moderation_status should be rejected
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Cool Skin"
    assert data["moderation_status"] == "rejected"

def test_impersonation_moderation():
    assert detect_impersonation_terms("make me look like joe biden") == True
    assert detect_impersonation_terms("a cool cyberpunk streamer") == False
    assert detect_impersonation_terms("I want to impersonate my boss") == True

def test_activate_rejected_skin():
    # Attempting to activate a skin with rejected moderation should fail
    file = create_valid_image_bytes()

    response = client.post(
        "/api/avatar/skins",
        headers=headers,
        data={
            "name": "Another Skin",
            "source_type": "upload",
            "consent_status": "pending"
        },
        files={"file": ("test2.png", file, "image/png")}
    )
    skin_id = response.json()["id"]

    # Try to activate
    activation = client.post(f"/api/avatar/skins/{skin_id}/activate", headers=headers)
    assert activation.status_code == 400
    assert "approved and consent confirmed" in activation.json()["detail"]

def test_start_session():
    response = client.post(
        "/api/avatar/session/start",
        headers=headers,
        json={"source_type": "webcam"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "live"
    assert "overlay_token" in data

def test_obs_source_invalid_token():
    response = client.get("/api/avatar/obs-source/invalid-token123")
    assert response.status_code == 404
