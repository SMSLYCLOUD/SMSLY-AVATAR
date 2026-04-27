from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ImageMetadata(BaseModel):
    face_count: Optional[int] = None
    estimated_subject_type: Optional[str] = None
    source: Optional[str] = None

class PromptGenerationRequest(BaseModel):
    user_prompt: str = Field(..., description="The user's core intent or prompt.")
    style_preset: Optional[str] = None
    scenario_preset: Optional[str] = None
    realism_level: Optional[str] = None
    safety_mode: Optional[str] = "strict"
    image_metadata: Optional[ImageMetadata] = None

class SafetyFlags(BaseModel):
    face_swap_risk: bool = False
    public_figure_risk: bool = False
    minor_risk: bool = False
    nsfw_risk: bool = False
    deception_risk: bool = False

class PromptGenerationResult(BaseModel):
    title: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    scene_description: str = ""
    style_tags: List[str] = []
    identity_preservation_notes: List[str] = []
    generation_mode: str = "identity_preserving_scene_replacement"
    model_recommendation: str = "sdxl / flux / identity-preserving pipeline"
    safety_flags: SafetyFlags = Field(default_factory=SafetyFlags)
    risk_level: str = "low"

class PromptGenerationResponse(BaseModel):
    result: Optional[PromptGenerationResult] = None
    provider: str = "openrouter"
    model: str = "unknown"
    latency: float = 0.0
    status: str = "success"
    warnings: List[str] = []
    blocked: bool = False
    block_reason: Optional[str] = None
    review_required: bool = False
