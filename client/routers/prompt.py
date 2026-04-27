from fastapi import APIRouter, HTTPException, Depends
from schemas.prompt_schemas import PromptGenerationRequest, PromptGenerationResponse
from services.openrouter_service import OpenRouterService
from services.prompt_generation_service import PromptGenerationService
import time

router = APIRouter()

# Simple dependency injection
def get_prompt_generation_service():
    openrouter_service = OpenRouterService()
    return PromptGenerationService(openrouter_service)

@router.post("/generate", response_model=PromptGenerationResponse)
async def generate_prompt_endpoint(
    request: PromptGenerationRequest,
    service: PromptGenerationService = Depends(get_prompt_generation_service)
):
    start_time = time.time()

    result, meta = await service.generate_prompt(request)

    latency = time.time() - start_time

    response = PromptGenerationResponse(
        result=result,
        provider="openrouter",
        model=meta.get("model", "unknown"),
        latency=round(latency, 3),
        status=meta.get("status", "success"),
        warnings=meta.get("warnings", []),
        blocked=meta.get("blocked", False),
        block_reason=meta.get("block_reason"),
        review_required=meta.get("blocked", False) or result.risk_level.lower() == "high"
    )

    return response
