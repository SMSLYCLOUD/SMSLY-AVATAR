import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("SMSLY_AVATAR_DATABASE_URL", "sqlite:///./data/smsly_avatar.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

def seed_demo_skins(db_session):
    from avatar_models import AvatarSkin
    import uuid

    if db_session.query(AvatarSkin).count() > 0:
        return

    demo_skins = [
        {"name": "Neon Host", "source_type": "synthetic_demo", "consent_status": "confirmed", "moderation_status": "approved"},
        {"name": "Cyber Studio", "source_type": "synthetic_demo", "consent_status": "confirmed", "moderation_status": "approved"},
        {"name": "Executive Avatar", "source_type": "synthetic_demo", "consent_status": "confirmed", "moderation_status": "approved"},
        {"name": "Streamer Pilot", "source_type": "synthetic_demo", "consent_status": "confirmed", "moderation_status": "approved"}
    ]

    for skin_data in demo_skins:
        skin = AvatarSkin(
            id=uuid.uuid4().hex,
            user_id="demo-user",
            **skin_data
        )
        db_session.add(skin)

    db_session.commit()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
