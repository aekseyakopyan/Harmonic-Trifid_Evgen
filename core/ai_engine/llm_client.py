import httpx
import json
import re
from typing import Optional
from core.config.settings import settings
from core.utils.logger import logger

class LLMClient:
    """
    LLM Client using OpenRouter API with fallback to local Ollama.
    """
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL or "deepseek/deepseek-chat"
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-bot.local",
            "X-Title": "Telegram AI Assistant"
        }

    async def generate_response(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> Optional[str]:
        """
        Generate a response using OpenRouter API.
        Automatically switches to fallback models on failure.
        """
        # Formulate list of models: Primary -> Fallback List
        models_to_try = [self.model] + settings.FALLBACK_MODELS
        models_to_try = list(dict.fromkeys(models_to_try))  # Dedup
        
        last_error = None
        
        for model_name in models_to_try:
            try:
                content = None
                
                logger.info(f"🔄 Trying Cloud Model: {model_name}")
                content = await self._generate_openrouter(model_name, prompt, system_prompt)

                if content:
                    # Success!
                    if model_name != self.model:
                        logger.warning(f"⚠️ [GWEN NOTICE] Successfully used fallback model: {model_name}")
                    
                    return content
                
            except Exception as e:
                logger.error(f"❌ Model {model_name} failed: {e}")
                last_error = e
                # Continue to next model...
        
        logger.error("🔥 All LLM models failed to generate a response.")
        return None

    async def _generate_openrouter(self, model_name: str, prompt: str, system_prompt: str) -> Optional[str]:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 8000
        }
        
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
            data = response.json()
            
            if "error" in data:
                error_msg = data.get("error", {}).get("message", str(data))
                raise Exception(f"Provider Error: {error_msg}")

            if "choices" in data and len(data["choices"]) > 0:
                return self._validate_content(data["choices"][0]["message"]["content"], model_name)
            
            return None

    async def call_api(self, model: str, prompt: str, text: str, timeout: float = 10.0) -> dict:
        """Structured call to OpenRouter with integrated parsing."""
        system_prompt = "Ты — экспертный фильтр лидов. Отвечай только СТРОГО валидным JSON."
        full_prompt = f"{prompt}\n\nТЕКСТ СООБЩЕНИЯ:\n{text}"
        
        response = await self._generate_openrouter(model, full_prompt, system_prompt)
        return self._parse_json_safe(response)

    def _parse_json_safe(self, text: Optional[str]) -> dict:
        """Безопасное извлечение JSON из текста ответа."""
        if not text:
            return {"is_real_lead": False, "role": "ERROR", "confidence": 0.0, "reason": "No response"}
            
        try:
            # Очистка от markdown
            clean_text = text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            logger.error(f"JSON Parse error: {e}")
        
        return {"is_real_lead": False, "role": "PARSE_ERROR", "confidence": 0.0, "reason": "Failed to parse JSON"}

    def _validate_content(self, content: str, model_name: str) -> Optional[str]:
        if not content:
            return None
            
        # Global cleaning: Remove quotes from ALL sources (EXCEPTION: JSON strings)
        if not (content.strip().startswith("{") or content.strip().startswith("[")):
            for quote in ['"', "'", "«", "»", "“", "”"]:
                content = content.replace(quote, "")
        content = content.strip()
        
        content_lower = content.lower().strip()
        
        # Technical error indicators in response text
        error_indicators = [
            "provider returned error", "rate limit", "quota exceeded", 
            "upstream error", "capacity reached", "error:", "exception:"
        ]
        
        if any(x in content_lower for x in error_indicators) and len(content) < 200:
             raise Exception(f"Model returned error text: {content[:100]}")
             
        return content

# Singleton instance
llm_client = LLMClient()
