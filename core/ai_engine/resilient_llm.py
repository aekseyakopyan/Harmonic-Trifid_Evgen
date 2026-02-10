"""
Resilient LLM Client с Circuit Breaker pattern для защиты от API failures.
Автоматический fallback: OpenRouter → Ollama → Heuristic-only
"""

from pybreaker import CircuitBreaker
from core.ai_engine.llm_client import LLMClient
from core.utils.structured_logger import get_logger
import time
import asyncio

logger = get_logger(__name__)


class ResilientLLMClient:
    """
    LLM клиент с защитой от сбоев через Circuit Breaker pattern.
    
    Состояния circuit breaker:
    - CLOSED: нормальная работа, все запросы идут к primary API
    - OPEN: после 5 failures, все запросы блокируются на 60s
    - HALF_OPEN: пробный запрос для проверки восстановления
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern для переиспользования circuit breakers"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Primary LLM client
        self.primary_client = LLMClient()
        
        # Circuit Breakers для каждого provider
        self.openrouter_breaker = CircuitBreaker(
            fail_max=5,                    # После 5 failures → OPEN
            reset_timeout=60,              # Recovery через 60s
            name="openrouter_circuit"
        )
        
        self.ollama_breaker = CircuitBreaker(
            fail_max=3,                    # Ollama менее стабильный
            reset_timeout=30,              # Быстрее восстановление
            name="ollama_circuit"
        )
        
        self._initialized = True
        
        logger.info(
            "resilient_llm_initialized",
            openrouter_state="closed",
            ollama_state="closed"
        )
    
    @property
    def circuit_state(self) -> dict:
        """
        Текущее состояние circuit breakers.
        
        Returns:
            {"openrouter": "closed|open|half_open", "ollama": "..."}
        """
        return {
            "openrouter": str(self.openrouter_breaker.current_state),
            "ollama": str(self.ollama_breaker.current_state)
        }
    
    async def call_with_fallback(
        self,
        prompt: str,
        text: str,
        timeout: int = 10
    ) -> dict:
        """
        Multi-level fallback для максимальной надежности.
        """
        start_time = time.time()
        
        # Попытка 1: OpenRouter
        try:
            result = await self._call_openrouter(prompt, text, timeout)
            result["method"] = "openrouter"
            result["latency_ms"] = int((time.time() - start_time) * 1000)
            
            logger.info(
                "llm_call_success",
                provider="openrouter",
                latency_ms=result["latency_ms"],
                circuit_state=self.openrouter_breaker.current_state
            )
            return result
            
        except Exception as e:
            logger.warning(
                "llm_primary_failed",
                provider="openrouter",
                circuit_state=self.openrouter_breaker.current_state,
                error=str(e)[:200]
            )
            
            # Попытка 2: Ollama fallback
            try:
                result = await self._call_ollama(prompt, text, timeout)
                result["method"] = "ollama_fallback"
                result["latency_ms"] = int((time.time() - start_time) * 1000)
                
                logger.info(
                    "llm_fallback_success",
                    provider="ollama",
                    latency_ms=result["latency_ms"],
                    circuit_state=self.ollama_breaker.current_state
                )
                return result
                
            except Exception as e2:
                logger.error(
                    "llm_all_failed",
                    openrouter_state=self.openrouter_breaker.current_state,
                    ollama_state=self.ollama_breaker.current_state,
                    error=str(e2)[:200]
                )
                
                # Попытка 3: Heuristic-only fallback
                return self._heuristic_only()
    
    async def _call_openrouter(self, prompt: str, text: str, timeout: int) -> dict:
        with self.openrouter_breaker:
            return await self.primary_client.call_api(
                model="deepseek/deepseek-chat",
                prompt=prompt,
                text=text,
                timeout=timeout
            )
    
    async def _call_ollama(self, prompt: str, text: str, timeout: int) -> dict:
        with self.ollama_breaker:
            return await self.primary_client.call_ollama(
                prompt=prompt,
                text=text,
                timeout=timeout
            )
    
    def _heuristic_only(self) -> dict:
        logger.warning(
            "llm_heuristic_fallback",
            reason="all_providers_unavailable"
        )
        
        return {
            "is_real_lead": None,
            "confidence": 0.5,
            "role": "unknown",
            "reason": "All LLM providers unavailable, using heuristic scoring only",
            "method": "heuristic_fallback",
            "red_flags": [],
            "latency_ms": 0
        }
    
    def get_health_status(self) -> dict:
        openrouter_state = str(self.openrouter_breaker.current_state)
        ollama_state = str(self.ollama_breaker.current_state)
        
        return {
            "healthy": openrouter_state != "open" or ollama_state != "open",
            "openrouter": {
                "state": openrouter_state,
                "fail_counter": self.openrouter_breaker.fail_counter
            },
            "ollama": {
                "state": ollama_state,
                "fail_counter": self.ollama_breaker.fail_counter
            }
        }


# Singleton instance для глобального использования
resilient_llm_client = ResilientLLMClient()
