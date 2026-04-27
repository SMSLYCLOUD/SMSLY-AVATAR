import os
import httpx
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OpenRouterService:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.default_model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.http_referer = os.environ.get("OPENROUTER_HTTP_REFERER", "http://localhost:8000")
        self.x_title = os.environ.get("OPENROUTER_X_TITLE", "Delulu Clone Local")
        self.timeout = float(os.environ.get("OPENROUTER_TIMEOUT", "10.0"))

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        retries: int = 2
    ) -> Dict[str, Any]:

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. OpenRouter service will fail.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.http_referer,
            "X-Title": self.x_title,
            "Content-Type": "application/json"
        }

        selected_model = model or self.default_model

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }

        logger.info(f"Calling OpenRouter API using model: {selected_model}")

        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )

                    response.raise_for_status()
                    data = response.json()

                    if "choices" not in data or not data["choices"]:
                        raise ValueError("No choices in OpenRouter response")

                    content = data["choices"][0]["message"]["content"]

                    # Try parsing as JSON immediately
                    try:
                        parsed_content = json.loads(content)
                        return {
                            "status": "success",
                            "model": data.get("model", selected_model),
                            "content": parsed_content
                        }
                    except json.JSONDecodeError:
                        logger.error(f"OpenRouter returned malformed JSON: {content}")
                        if attempt == retries:
                            return {
                                "status": "error",
                                "model": selected_model,
                                "error": "Failed to parse JSON response from LLM"
                            }
                        continue # Retry

            except httpx.HTTPStatusError as e:
                logger.error(f"OpenRouter HTTP Error: {e.response.status_code} - {e.response.text}")
                if attempt == retries:
                    return {
                        "status": "error",
                        "model": selected_model,
                        "error": f"HTTP {e.response.status_code}"
                    }
            except httpx.RequestError as e:
                logger.error(f"OpenRouter Request Error: {str(e)}")
                if attempt == retries:
                    return {
                        "status": "error",
                        "model": selected_model,
                        "error": "Request failed (timeout or network error)"
                    }
            except Exception as e:
                logger.error(f"OpenRouter Unexpected Error: {str(e)}")
                if attempt == retries:
                    return {
                        "status": "error",
                        "model": selected_model,
                        "error": str(e)
                    }

            logger.info(f"Retrying OpenRouter request (Attempt {attempt + 1}/{retries})...")

        return {
            "status": "error",
            "model": selected_model,
            "error": "Max retries exceeded"
        }
