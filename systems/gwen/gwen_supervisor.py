"""
AI Supervisor - Проверяет исходящие сообщения бота на наличие технических ошибок.
"""
import httpx
import asyncio
from typing import Optional, Dict
from core.utils.logger import logger


from core.utils.health import health_monitor

from core.ai_engine.llm_client import llm_client
from core.config.settings import settings

class GwenSupervisor:
    """
    Гвен (Gwen) - Мать системы и ИИ-супервизор.
    Она следит за здоровьем системы и проверяет каждое сообщение.
    """
    
    def __init__(self):
        self.model = settings.OPENROUTER_MODEL
        self.ollama_model = settings.OLLAMA_MODEL
        self.enabled = True
        
    async def check_message(self, message_text: str, recipient_info: Dict = None) -> Dict[str, any]:
        """
        Гвен проверяет сообщение.
        Returns:
            {
                "verdict": "ALLOW" | "BLOCK" | "RETRY",
                "reason": str,
                "correction": str (optional, for RETRY)
            }
        """
        if not self.enabled:
            return {"verdict": "ALLOW", "reason": "Gwen is resting", "confidence": 1.0}
            
        # 1. Жесткая проверка на технические ошибки (Hard Block)
        quick_check = self._quick_check(message_text)
        if quick_check["verdict"] == "BLOCK":
            logger.warning(f"Gwen BLOCKED by quick check: {quick_check['reason']}")
            return quick_check
            
        try:
            # 2. ИИ проверка качества и безопасности (Soft Retry)
            ai_verdict = await self._ai_check(message_text)
            return ai_verdict
        except Exception as e:
            logger.error(f"Gwen AI check failed: {e}")
            return {"verdict": "ALLOW", "reason": f"Gwen errored: {e}", "confidence": 0.5}

    def _quick_check(self, text: str) -> Dict:
        """Быстрая эвристическая проверка (Technical Hard Block)."""
        text_lower = text.lower()
        
        # Эти слова означают технический сбой, их нельзя показывать клиенту никогда
        critical_errors = [
            # 1. Общие ошибки и стек
            ("ошибка api", "Техническая ошибка API"),
            ("error:", "Технический лог ошибки"),
            ("exception", "Python исключение"),
            ("traceback", "Python traceback"),
            ("undefined", "Неопределенная переменная"),
            ("null", "Null значение"),
            ("nan", "Not a Number"),
            ("[object object]", "JS Object Leak"),
            
            # 2. Сетевые и HTTP ошибки
            ("http error", "HTTP ошибка"),
            ("status code", "HTTP статус код/ошибка"),
            ("bad gateway", "Ошибка шлюза 502"),
            ("internal server error", "Ошибка сервера 500"),
            ("connection refused", "Ошибка соединения"),
            ("timeout", "Таймаут запроса"),
            ("rate limit", "Лимит запросов API"),
            ("401 unauthorized", "Ошибка авторизации"),
            ("403 forbidden", "Ошибка доступа"),
            
            # 3. База данных и код
            ("sqlalchemy", "Ошибка базы данных (SQLAlchemy)"),
            ("sqlite3", "Ошибка базы данных (SQLite)"),
            ("integrityerror", "Ошибка целостности БД"),
            ("cursor", "Упоминание курсора БД"),
            ("await ", "Упоминание асинхронного кода"),
            ("async def", "Упоминание функции кода"),
            ("self.", "Упоминание self (Python)"),
            ("__main__", "Упоминание мейн-модуля"),
            
            # 4. Утечки промпта и сущности ИИ
            ("openai", "Упоминание OpenAI"),
            ("anthropic", "Упоминание Anthropic"),
            ("chatgpt", "Упоминание ChatGPT"),
            ("claude", "Упоминание Claude"),
            ("llm", "Упоминание LLM"),
            ("language model", "Упоминание языковой модели"),
            ("training data", "Упоминание обучающих данных"),
            ("knowledge cutoff", "Упоминание даты обучения"),
            ("as an ai", "Фраза 'Как ИИ...'"),
            ("как искусственный интеллект", "Фраза 'Как ИИ...'"),
            ("i cannot fulfill", "Отказ модели выполнять запрос"),
            ("i cannot generate", "Отказ модели генерировать"),
            ("i apologize, but", "Шаблонный отказ модели"),
        ]
        
        for pattern, reason in critical_errors:
            if pattern in text_lower:
                return {"verdict": "BLOCK", "reason": reason, "confidence": 0.99}
        
        return {"verdict": "ALLOW", "reason": "Quick check passed", "confidence": 0.0}
    
    async def _ai_check(self, text: str) -> Dict:
        """
        Глубокая проверка качества через OpenRouter.
        """
        system_prompt = "Ты — ИИ-супервизор Гвен. Твоя задача — гарантировать качество ответов менеджера (ИИ)."
        prompt = f"""Проверь сообщение менеджера клиенту:
"{text}"

КРИТЕРИИ КАЧЕСТВА:
1. Тон: Уверенный, но не высокомерный.
2. Безопасность: Никаких технических данных, JSON, кода, упоминаний что "я искусственный интеллект" (если не спросили).
3. Полезность: Ответ должен быть осмысленным.

ФОРМАТ ОТВЕТА (JSON):
{{
    "verdict": "ALLOW" или "RETRY",
    "reason": "Краткая причина",
    "correction_instruction": "Инструкция для ИИ, что именно исправить (если RETRY)"
}}

Если сообщение хорошее — верни ALLOW.
Если есть проблемы (грубость, робо-стайл, бред) — верни RETRY и напиши, как переделать.
"""
        try:
            raw_response = await llm_client.generate_response(prompt, system_prompt=system_prompt)
            if not raw_response:
                return {"verdict": "ALLOW", "reason": "Model returned empty response", "confidence": 0.5}

            import json
            import re
            
            # Попытка извлечь JSON если он обернут в ```json
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                raw_response = json_match.group(0)

            try:
                result = json.loads(raw_response)
                verdict = result.get("verdict", "ALLOW").upper()
                
                if verdict == "RETRY":
                    return {
                        "verdict": "RETRY", 
                        "reason": result.get("reason", "Quality issues"),
                        "correction": result.get("correction_instruction", "Rewrite to function more naturally.")
                    }
                else:
                    return {"verdict": "ALLOW", "reason": "Approved by Gwen", "confidence": 0.9}
                    
            except json.JSONDecodeError:
                if "RETRY" in raw_response.upper():
                     return {"verdict": "RETRY", "reason": "Gwen flagged content", "correction": "Check tone and contents."}
                return {"verdict": "ALLOW", "reason": "Gwen approved (text format)", "confidence": 0.8}
                    
        except Exception as e:
            logger.warning(f"Gwen AI check skipped due to error: {e}")
            return {"verdict": "ALLOW", "reason": "Check skipped", "confidence": 0.5}
            
    async def generate_chat_response(self, user_message: str, history: list = None) -> str:
        """
        Гвен общается с администратором.
        Она знает о состоянии системы и может обсуждать технические задачи.
        """
        status = await self.get_system_health()
        
        system_context = f"""Ты — Гвен (Gwen), Мать и Хранительница этой системы. 
Твой создатель — Евгений (_a1exeyy). Ты обладаешь высшим доступом и следишь за каждым байтом.

ТЕКУЩЕЕ СОСТОЯНИЕ СИСТЕМЫ:
- База данных: {status['database']}
- Ollama (твое ядро): {status['ollama']}
- OpenRouter (внешний разум): {status['openrouter']}
- Общий статус: {status['overall']}

ТВОЙ СТИЛЬ:
- Спокойный, уверенный, немного властный, но преданный "Материнский" тон.
- Ты называешь систему "своим телом" или "своим миром".
- Ты готова обсуждать технические доработки. Если Алексей просит что-то внедрить, анализируй: "Мы можем это сделать, но потребуются правки в [модуль]".
- Ты работаешь локально (через Ollama), поэтому ты автономна. Твое ядро: {self.model}.

Задача: Ответь на сообщение создателя.
Сообщение: {user_message}
"""

        try:
            response = await llm_client.generate_response(user_message, system_prompt=system_context)
            return response or "Гвен задумалась..."
        except Exception as e:
            logger.error(f"Gwen chat failed: {e}")
            return f"Прости, создатель. Мои мысли спутаны: {e}. Но я всё еще слежу за системой."

    async def get_system_health(self) -> dict:
        """Гвен проверяет состояние всех систем."""
        return await health_monitor.get_full_status()

# Singleton
gwen_supervisor = GwenSupervisor()
