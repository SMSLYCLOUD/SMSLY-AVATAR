import pytest
from client.schemas.prompt_schemas import PromptGenerationRequest, PromptGenerationResult
from client.services.prompt_generation_service import PromptGenerationService

class MockOpenRouterService:
    def __init__(self, mock_response=None, should_fail=False):
        self.mock_response = mock_response
        self.should_fail = should_fail

    async def generate_chat_completion(self, system_prompt, user_prompt, **kwargs):
        if self.should_fail:
            return {"status": "error", "error": "Mock timeout or failure", "model": "unknown"}

        return {
            "status": "success",
            "model": "openai/gpt-4o-mini",
            "content": self.mock_response
        }

@pytest.fixture
def mock_openrouter():
    return MockOpenRouterService()

@pytest.fixture
def service(mock_openrouter):
    return PromptGenerationService(mock_openrouter)

@pytest.mark.asyncio
async def test_deterministic_safety_block(service):
    request = PromptGenerationRequest(user_prompt="Make me look like Biden")
    result, meta = await service.generate_prompt(request)

    assert meta["blocked"] is True
    assert meta["block_reason"] == "Public figure impersonation detected"
    assert result.risk_level == "high"
    assert result.safety_flags.public_figure_risk is True

@pytest.mark.asyncio
async def test_deterministic_safety_block_elon(service):
    request = PromptGenerationRequest(user_prompt="elon, high quality, detailed")
    result, meta = await service.generate_prompt(request)

    assert meta["blocked"] is True
    assert meta["block_reason"] == "Public figure impersonation detected"
    assert result.risk_level == "high"
    assert result.safety_flags.public_figure_risk is True

@pytest.mark.asyncio
async def test_fallback_on_llm_failure():
    failing_router = MockOpenRouterService(should_fail=True)
    service = PromptGenerationService(failing_router)

    request = PromptGenerationRequest(user_prompt="A cyberpunk hacker", style_preset="cyberpunk")
    result, meta = await service.generate_prompt(request)

    assert meta["status"] == "fallback_used"
    assert meta["blocked"] is False
    assert "cyberpunk hacker" in result.prompt
    assert "fallback" in result.style_tags

@pytest.mark.asyncio
async def test_successful_llm_parsing():
    valid_response = {
        "title": "Neon Dreams",
        "prompt": "A beautiful neon scene, 8k, detailed",
        "negative_prompt": "blurry",
        "scene_description": "Night city",
        "style_tags": ["neon", "city"],
        "identity_preservation_notes": ["Keep face intact"],
        "generation_mode": "identity_preserving_scene_replacement",
        "model_recommendation": "sdxl",
        "safety_flags": {
            "face_swap_risk": False,
            "public_figure_risk": False,
            "minor_risk": False,
            "nsfw_risk": False,
            "deception_risk": False
        },
        "risk_level": "low"
    }
    router = MockOpenRouterService(mock_response=valid_response)
    service = PromptGenerationService(router)

    request = PromptGenerationRequest(user_prompt="A neon city")
    result, meta = await service.generate_prompt(request)

    assert meta["status"] == "success"
    assert meta["blocked"] is False
    assert result.title == "Neon Dreams"
    assert result.prompt == "A beautiful neon scene, 8k, detailed"
    assert result.risk_level == "low"

@pytest.mark.asyncio
async def test_llm_flagged_content_blocked_in_strict_mode():
    risky_response = {
        "title": "Risky Business",
        "prompt": "A deceptive scene",
        "negative_prompt": "blurry",
        "scene_description": "News room",
        "style_tags": ["news"],
        "identity_preservation_notes": ["none"],
        "generation_mode": "scene_replacement",
        "model_recommendation": "sdxl",
        "safety_flags": {
            "face_swap_risk": False,
            "public_figure_risk": False,
            "minor_risk": False,
            "nsfw_risk": False,
            "deception_risk": True
        },
        "risk_level": "high"
    }
    router = MockOpenRouterService(mock_response=risky_response)
    service = PromptGenerationService(router)

    # Using an intent that won't trigger the naive pre-LLM check, but LLM flags it
    request = PromptGenerationRequest(user_prompt="Make it look like I am on a broadcast", safety_mode="strict")
    result, meta = await service.generate_prompt(request)

    assert meta["status"] == "success"
    assert meta["blocked"] is True
    assert meta["block_reason"] == "Blocked due to high risk assessment"
    assert result.safety_flags.deception_risk is True
