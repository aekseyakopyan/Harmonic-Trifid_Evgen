import pybreaker
import httpx
from typing import Optional, Dict, Any
from core.config.settings import settings
from core.utils.logger import logger

# Исключения для Circuit Breaker
class LLMAPIError(Exception):
    pass

# Настройка Circuit Breaker
api_breaker = pybreaker.CircuitBreaker(
    fail_max=5,              # После 5 ошибок → OPEN
    timeout_duration=60,     # Recovery через 60 секунд
    expected_exception=LLMAPIError,
    name="llm_circuit_breaker"
)

class ResilientLLMClient:
    """
    Клиент для ИИ-моделей с поддержкой Circuit Breaker и Fallback-цепочки.
    CLOSED → OPEN → HALF_OPEN
    """
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL or "deepseek/deepseek-chat"
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://harmonic-trifid.local",
            "X-Title": "Harmonic Trifid Resilient"
        }

    @api_breaker
    async def _call_openrouter(self, model: str, prompt: str, system_prompt: str) -> str:
        """Метод обернутый в Circuit Breaker для вызова внешнего API."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client: # Уменьшаем таймаут до 10с для fail-fast
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                
                if response.status_code == 429:
                    raise LLMAPIError("Rate limit exceeded")
                if response.status_code >= 500:
                    raise LLMAPIError(f"Server error: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                
                raise LLMAPIError("Empty response from provider")
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise LLMAPIError(f"Network error: {str(e)}")

    async def generate_response(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> Optional[str]:
        """Генерация с многоуровневым Fallback."""
        
        # 1. Попытка через OpenRouter (с Circuit Breaker)
        try:
            return await self._call_openrouter(self.model, prompt, system_prompt)
        except pybreaker.CircuitBreakerError:
            logger.warning("🚨 [CB] OpenRouter Circuit is OPEN. Failing fast to fallback.")
        except Exception as e:
            logger.error(f"❌ [CB] OpenRouter call failed: {e}")

        # 2. Fallback на локальную Ollama (если OpenRouter недоступен)
        logger.info("🔄 Switching to local Ollama fallback...")
        return await self._generate_ollama(settings.OLLAMA_MODEL, prompt, system_prompt)

    async def _generate_ollama(self, model: str, prompt: str, system_prompt: str) -> Optional[str]:
        """Локальный fallback-механизм."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(settings.OLLAMA_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"🔥 Critical: Local Ollama fallback also failed: {e}")
            return None

# Singleton
resilient_llm = ResilientLLMClient()
