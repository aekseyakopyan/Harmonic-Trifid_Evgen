import httpx
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
        Generate a response using OpenRouter API with fallback models and local Ollama.
        Automatically switches models on failure.
        """
        # Formulate list of models: Primary -> Fallback List -> Local Ollama
        models_to_try = [self.model] + settings.FALLBACK_MODELS
        models_to_try = list(dict.fromkeys(models_to_try))  # Dedup
        
        # Add local Ollama as the last resort
        ollama_model_id = f"ollama/{settings.OLLAMA_MODEL}"
        models_to_try.append(ollama_model_id)

        last_error = None
        
        for model_name in models_to_try:
            try:
                content = None
                
                # BRANCH 1: Local Ollama
                if model_name.startswith("ollama/"):
                    real_model = model_name.replace("ollama/", "")
                    logger.info(f"🔄 Switching to LOCAL OLLAMA model: {real_model}")
                    content = await self._generate_ollama(real_model, prompt, system_prompt)

                # BRANCH 2: OpenRouter Cloud
                else:
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
        
        logger.error("🔥 All LLM models (Cloud + Local) failed to generate a response.")
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

    async def _generate_ollama(self, model_name: str, prompt: str, system_prompt: str) -> Optional[str]:
        # Force Russian instruction for Ollama locally if needed
        full_prompt = prompt
        if "отвечай только на русском" not in prompt.lower():
            full_prompt = f"{prompt}\n\n[ОБЯЗАТЕЛЬНО: ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ, БЕЗ КАВЫЧЕК]"

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.6,
                "top_p": 0.8
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    settings.OLLAMA_URL,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                if content:
                    # Post-process: Remove ALL types of quotes
                    for quote in ['"', "'", "«", "»", "“", "”"]:
                        content = content.replace(quote, "")
                    content = content.strip()
                    
                    # Detect if it's still English (Jessica syndrome)
                    latin_chars = sum(1 for c in content[:100] if 'a' <= c.lower() <= 'z')
                    if latin_chars > 15 and len(content) > 20:
                        logger.warning(f"⚠️ Detected English bias in response from {model_name}. Retrying with absolute language lock...")
                        # Final attempt: Very short, aggressive instruction
                        payload["messages"][1]["content"] = f"ПИШИ ТОЛЬКО НА РУССКОМ. НИКАКОГО АНГЛИЙСКОГО. БЕЗ КАВЫЧЕК. ТЕМА: {prompt[:100]}"
                        payload["options"]["temperature"] = 0.3 # Reduce randomness
                        response = await client.post(settings.OLLAMA_URL, json=payload)
                        data = response.json()
                        content = data.get("message", {}).get("content", "").strip()
                        for quote in ['"', "'", "«", "»", "“", "”"]:
                            content = content.replace(quote, "")

                return content
            except httpx.ConnectError:
                raise Exception("Ollama connection refused (Is it running?)")

    async def call_api(self, model: str, prompt: str, text: str, timeout: float = 10.0) -> dict:
        """Structured call to OpenRouter with integrated parsing."""
        system_prompt = "Ты — экспертный фильтр лидов. Отвечай только СТРОГО валидным JSON."
        full_prompt = f"{prompt}\n\nТЕКСТ СООБЩЕНИЯ:\n{text}"
        
        response = await self._generate_openrouter(model, full_prompt, system_prompt)
        return self._parse_json_safe(response)

    async def call_ollama(self, prompt: str, text: str, timeout: float = 10.0) -> dict:
        """Structured call to local Ollama with integrated parsing."""
        system_prompt = "Ты — экспертный фильтр лидов. Отвечай только СТРОГО валидным JSON."
        full_prompt = f"{prompt}\n\nТЕКСТ СООБЩЕНИЯ:\n{text}"
        
        response = await self._generate_ollama(settings.OLLAMA_MODEL, full_prompt, system_prompt)
        return self._parse_json_safe(response)

    def _parse_json_safe(self, text: Optional[str]) -> dict:
        """Безопасное извлечение JSON из текста ответа."""
        if not text:
            return {"is_real_lead": False, "role": "ERROR", "confidence": 0.0, "reason": "No response"}
            
        try:
            # Очистка от markdown
            clean_text = text.replace("```json", "").replace("```", "").strip()
            import re
            match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if match:
                import json
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
