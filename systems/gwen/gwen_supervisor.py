"""
AI Supervisor - Проверяет исходящие сообщения бота на наличие технических ошибок.
"""
import httpx
from typing import Dict
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
        Оценка качества ответа через OpenRouter (быстрая модель-супервизор).
        """
        import json
        import re

        system_prompt = (
            "Ты — Гвен, супервизор цифрового агентства Evium (SEO, контекстная реклама, Авито, SMM, сайты). "
            "Алексей — менеджер-бот, ведёт холодные продажи через Telegram. "
            "Твоя задача: проверить его ответ клиенту перед отправкой."
        )

        prompt = f"""Проверь сообщение Алексея клиенту:

\"\"\"{text}\"\"\"

КРИТЕРИИ (проверяй по порядку):

1. BLOCK — немедленная блокировка, если в тексте:
   - Упоминание ИИ, GPT, Claude, OpenAI, LLM, нейросети
   - Python-код, traceback, JSON-объекты, технические ошибки
   - Фраза "я не могу", "как языковая модель", "мои данные ограничены"

2. RETRY — перегенерация, если:
   - Начинается с "Вижу, что", "Заметил, что", "Увидел запрос", "Вижу ваш запрос"
   - Содержит домен или URL (кроме teletype.in — это разрешённые кейсы)
   - Более одного вопроса в сообщении
   - Обращение по имени в приветствии (например "Привет, Татьяна!")
   - Ответ явно не по теме запроса клиента
   - Текст > 10 предложений или < 2 предложений
   - Агрессивное давление ("купи прямо сейчас", "последний шанс")

3. ALLOW — всё остальное.

Ответь строго JSON:
{{"verdict": "ALLOW" | "BLOCK" | "RETRY", "reason": "одна фраза", "correction": "что исправить (только для RETRY)"}}"""

        try:
            payload = {
                "model": settings.SUPERVISOR_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.1
            }
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://telegram-bot.local",
                "X-Title": "Gwen Supervisor"
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"].strip()

            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                verdict = result.get("verdict", "ALLOW").upper()
                if verdict == "RETRY":
                    return {
                        "verdict": "RETRY",
                        "reason": result.get("reason", "Quality issues"),
                        "correction": result.get("correction", "Rewrite more naturally.")
                    }
                elif verdict == "BLOCK":
                    return {"verdict": "BLOCK", "reason": result.get("reason", "Blocked by Gwen AI")}
                return {"verdict": "ALLOW", "reason": "Approved by Gwen"}

            # Не смогли разобрать JSON — пропускаем
            return {"verdict": "ALLOW", "reason": "Gwen response unparseable"}

        except Exception as e:
            logger.warning(f"Gwen AI check skipped: {e}")
            return {"verdict": "ALLOW", "reason": f"Check skipped: {e}"}
            
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
- OpenRouter (внешний разум): {status['openrouter']}
- Общий статус: {status['overall']}

ТВОЙ СТИЛЬ:
- Спокойный, уверенный, немного властный, но преданный "Материнский" тон.
- Ты называешь систему "своим телом" или "своим миром".
- Ты готова обсуждать технические доработки. Если Алексей просит что-то внедрить, анализируй: "Мы можем это сделать, но потребуются правки в [модуль]".
- Твое главное ядро: {self.model}.

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
