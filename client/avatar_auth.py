from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
import os

API_KEY_NAME = "X-SMSLY-User-ID"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_current_avatar_user(api_key: str = Security(api_key_header)):
    dev_auth = os.environ.get("SMSLY_AVATAR_DEV_AUTH", "true").lower() == "true"
    demo_user = os.environ.get("SMSLY_AVATAR_DEMO_USER_ID", "demo-user")

    if api_key:
        return api_key
    elif dev_auth:
        return demo_user
    else:
        raise HTTPException(status_code=401, detail="Missing X-SMSLY-User-ID header.")
