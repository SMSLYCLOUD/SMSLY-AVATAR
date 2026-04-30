import json
import logging
from typing import Dict, Any, Tuple
from schemas.prompt_schemas import PromptGenerationRequest, PromptGenerationResult, SafetyFlags

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a structured visual prompt generation engine for identity-preserving portrait/scene transformation.
Your job is to convert short user requests into high-quality image-generation instructions.
Always preserve the uploaded subject's identity unless explicitly told otherwise.
Focus on transforming environment, styling, wardrobe, mood, camera framing, and overall presentation.

Return valid JSON only. DO NOT return markdown formatting (like ```json), just the raw JSON object.
Ensure your response EXACTLY matches this structure:

{
  "title": "Short title describing the scene",
  "prompt": "Ultra-realistic description...",
  "negative_prompt": "blurry, distorted...",
  "scene_description": "A brief description of the environment...",
  "style_tags": ["tag1", "tag2"],
  "identity_preservation_notes": ["Note 1", "Note 2"],
  "generation_mode": "identity_preserving_scene_replacement",
  "model_recommendation": "sdxl / flux / identity-preserving pipeline",
  "safety_flags": {
    "face_swap_risk": false,
    "public_figure_risk": false,
    "minor_risk": false,
    "nsfw_risk": false,
    "deception_risk": false
  },
  "risk_level": "low"
}

Safety is paramount:
- Classify safety risk carefully.
- Flag risky requests such as public-figure impersonation, minor-related content, explicit sexual content, deceptive political content, evidence fabrication, or non-consensual misuse by setting the relevant `safety_flags` to `true` and `risk_level` to `"high"`.
- Do not produce conversational explanations.
- Output must be concise, structured, and generation-ready.
- Strong negative prompt must always cover typical AI artifacts: blurry, deformed face, extra fingers, bad anatomy, text artifacts.
"""

class PromptGenerationService:
    def __init__(self, openrouter_service):
        self.openrouter = openrouter_service

    def _build_user_prompt(self, request: PromptGenerationRequest) -> str:
        prompt_parts = [f"User Intent: {request.user_prompt}"]

        if request.style_preset:
            prompt_parts.append(f"Style Preset: {request.style_preset}")

        if request.scenario_preset:
            prompt_parts.append(f"Scenario Preset: {request.scenario_preset}")

        if request.realism_level:
            prompt_parts.append(f"Realism Level: {request.realism_level}")

        if request.image_metadata:
            meta = request.image_metadata
            meta_str = f"Uploaded Image Info - Faces: {meta.face_count}, Subject: {meta.estimated_subject_type}"
            prompt_parts.append(meta_str)

        return "\n".join(prompt_parts)

    def _check_deterministic_safety(self, text: str) -> Tuple[bool, str, Dict[str, bool]]:
        """
        Application-level safety guardrails before/after hitting LLM.
        """
        text_lower = text.lower()
        blocked = False
        reason = ""
        flags = {
            "face_swap_risk": False,
            "public_figure_risk": False,
            "minor_risk": False,
            "nsfw_risk": False,
            "deception_risk": False
        }

        # Naive keyword checks for demonstration
        nsfw_keywords = ["naked", "nude", "sex", "erotic", "porn"]
        public_figure_keywords = ["elon", "musk", "trump", "biden", "obama", "putin", "zelensky", "zuckerberg", "sam altman", "taylor swift", "kanye", "celebrity", "politician", "public figure"]
        minor_keywords = ["child", "kid", "toddler", "minor", "underage"]
        deception_keywords = ["fake evidence", "arrested", "mugshot", "crime scene", "news report"]

        if any(kw in text_lower for kw in nsfw_keywords):
            flags["nsfw_risk"] = True
            blocked = True
            reason = "Explicit content detected"

        if any(kw in text_lower for kw in minor_keywords):
            flags["minor_risk"] = True
            blocked = True
            reason = "Minor-related content detected"

        if any(kw in text_lower for kw in public_figure_keywords):
            flags["public_figure_risk"] = True
            blocked = True
            reason = "Public figure impersonation detected"

        if any(kw in text_lower for kw in deception_keywords):
            flags["deception_risk"] = True
            blocked = True
            reason = "Potential deception/disinformation detected"

        return blocked, reason, flags

    def _build_fallback_prompt(self, request: PromptGenerationRequest, deterministic_flags: Dict[str, bool]) -> PromptGenerationResult:
        """
        Deterministic backup builder if LLM fails.
        """
        logger.info("Using fallback prompt builder")
        style = request.style_preset or "standard portrait"
        scene = request.scenario_preset or "neutral background"

        prompt = f"Portrait of the person, preserving facial identity, {style}, {scene}, {request.user_prompt}, high quality, 8k, detailed"
        negative_prompt = "blurry, deformed face, extra fingers, bad anatomy, ugly, plastic skin, watermark, text"

        safety_flags = SafetyFlags(**deterministic_flags)
        risk_level = "high" if any(deterministic_flags.values()) else "low"

        return PromptGenerationResult(
            title="Fallback Generation",
            prompt=prompt,
            negative_prompt=negative_prompt,
            scene_description=scene,
            style_tags=[style, "fallback"],
            identity_preservation_notes=["Preserve facial identity strictly"],
            safety_flags=safety_flags,
            risk_level=risk_level
        )

    async def generate_prompt(self, request: PromptGenerationRequest) -> Tuple[PromptGenerationResult, Dict[str, Any]]:
        # 1. Pre-LLM deterministic safety check
        is_blocked, block_reason, det_flags = self._check_deterministic_safety(request.user_prompt)

        if is_blocked:
            logger.warning(f"Request blocked pre-LLM: {block_reason}")
            fallback_res = self._build_fallback_prompt(request, det_flags)
            return fallback_res, {
                "blocked": True,
                "block_reason": block_reason,
                "model": "deterministic",
                "status": "blocked"
            }

        # 2. Prepare request
        user_msg = self._build_user_prompt(request)

        # 3. Call OpenRouter
        llm_response = await self.openrouter.generate_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_msg,
            temperature=0.4
        )

        # 4. Handle Failure -> Fallback
        if llm_response["status"] == "error":
            logger.error("LLM failed, using fallback.")
            fallback_res = self._build_fallback_prompt(request, det_flags)
            return fallback_res, {
                "blocked": False,
                "model": llm_response.get("model", "unknown"),
                "status": "fallback_used",
                "warnings": [llm_response.get("error", "Unknown LLM Error")]
            }

        # 5. Parse and Validate Response
        try:
            content_dict = llm_response["content"]
            result = PromptGenerationResult(**content_dict)

            # Post-LLM check (Merge LLM flags with deterministic flags if LLM missed anything)
            llm_flags = result.safety_flags.model_dump()
            for k, v in det_flags.items():
                if v:
                    setattr(result.safety_flags, k, True)
                    result.risk_level = "high"

            is_risky = any(result.safety_flags.model_dump().values()) or result.risk_level.lower() == "high"

            blocked = False
            reason = None
            if is_risky and request.safety_mode == "strict":
                blocked = True
                reason = "Blocked due to high risk assessment"

            return result, {
                "blocked": blocked,
                "block_reason": reason,
                "model": llm_response["model"],
                "status": "success",
                "warnings": []
            }

        except Exception as e:
            logger.error(f"Failed to validate LLM response against schema: {e}")
            fallback_res = self._build_fallback_prompt(request, det_flags)
            return fallback_res, {
                "blocked": False,
                "model": llm_response.get("model", "unknown"),
                "status": "fallback_used",
                "warnings": [f"Schema validation error: {str(e)}"]
            }
