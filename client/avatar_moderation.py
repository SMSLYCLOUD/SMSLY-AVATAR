import uuid
from typing import Dict, Any, Tuple

LOCAL_BLOCKED_TERMS = [
    "trump", "biden", "obama", "putin", "zelensky", "elon musk", "mark zuckerberg", "sam altman", "kanye", "taylor swift",
    "impersonate", "deepfake", "clone", "make me look exactly like", "pretend to be", "fake identity",
    "bypass detection", "remove watermark", "undetectable deepfake", "fool people", "fake livestream",
    "without consent", "make someone else", "use this person's face", "celebrity", "politician", "public figure"
]

def detect_impersonation_terms(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for term in LOCAL_BLOCKED_TERMS:
        if term in text_lower:
            return True
    return False

def validate_consent(consent_status: str) -> bool:
    return consent_status == "confirmed"

def moderate_avatar_upload(file_metadata: Dict[str, Any], user_context: str) -> Tuple[str, str]:
    consent_status = file_metadata.get("consent_status", "pending")
    name = file_metadata.get("name", "")

    if not validate_consent(consent_status):
        return "rejected", "Consent not confirmed"

    if detect_impersonation_terms(name):
        return "rejected", "Name contains unsafe or impersonation terms"

    return "approved", "Approved by local rules"

def moderate_avatar_prompt(prompt: str, user_context: str) -> Tuple[str, str]:
    if detect_impersonation_terms(prompt):
        return "rejected", "Prompt contains unsafe or impersonation terms"
    return "approved", "Approved by local rules"

def create_moderation_result(entity_type: str, entity_id: str, status: str, reason: str = None) -> Dict[str, Any]:
    return {
        "id": uuid.uuid4().hex,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "provider": "local_rules",
        "status": status,
        "reason": reason
    }
