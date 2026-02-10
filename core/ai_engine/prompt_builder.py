from typing import List, Optional
from core.database.models import Case, Service
from core.config.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, FOLLOW_UP_PROMPT_TEMPLATE

class PromptBuilder:
    @staticmethod
    def get_personality() -> str:
        """Возвращает базовую личность Алексея."""
        return SYSTEM_PROMPT

    @staticmethod
    def build_system_prompt(task_instruction: str) -> str:
        """
        Собирает полный системный промпт:
        1. Базовая личность
        2. Краткая инструкция (контекст задачи)
        """
        return f"{SYSTEM_PROMPT}\n\n## ТВОЯ ТЕКУЩАЯ ЗАДАЧА:\n{task_instruction}"

    @staticmethod
    def build_user_prompt(
        query: str, 
        user_name: str,
        cases: List[Case], 
        external_cases: List[dict] = None,
        service: Optional[Service] = None,
        category: Optional[str] = None,
        style_profile: Optional[str] = None,
        context_memory: Optional[str] = None,
        history_text: Optional[str] = None,
        current_emotion: str = "skeptical",
        sales_materials: List[dict] = None
    ) -> str:
        context = ""
        
        if context_memory:
            context += f"ЧТО МЫ УЖЕ ЗНАЕМ О КЛИЕНТЕ:\n{context_memory}\n\n"
            
        if style_profile:
            context += f"СТИЛЬ ОБЩЕНИЯ КЛИЕНТА (подстраивайся под него):\n{style_profile}\n\n"

        if category and category != "general":
            context += f"Категория запроса: {category}\n"
            
        if service:
            context += f"Услуга: {service.name} — {service.price_range}\n"

        if sales_materials:
            context += "\nБАЗА ЗНАНИЙ ПО ПРОДАЖАМ (используй эти принципы и скрипты):\n"
            for mat in sales_materials:
                context += f"--- Источник: {mat['source']} ---\n{mat['content']}\n"
            
        if cases:
            context += "\nНаши релевантные кейсы (используй их в первую очередь):\n"
            for case in cases:
                context += f"- {case.title}: {case.results}\n"
        
        if external_cases:
            context += "\nДополнительные кейсы из нашей практики (2024-2025):\n"
            for ec in external_cases:
                context += f"- {ec['title']}: {ec['description']}\n"
        
        from core.config.prompts import EMOTIONS
        emotion_description = EMOTIONS.get(current_emotion, EMOTIONS["skeptical"])
            
        return USER_PROMPT_TEMPLATE.format(
            context=context, 
            query=query,
            user_name=user_name,
            conversation_history=history_text or "Нет предыдущих сообщений",
            current_emotion=emotion_description
        )

    @staticmethod
    def build_follow_up_prompt(
        history_text: str,
        context_memory: str = "",
        style_profile: str = "",
        days_since_last_message: int = 0,
        last_message: str = ""
    ) -> str:
        """Промпт для генерации напоминания."""
        context = ""
        if context_memory:
            context += f"ЧТО МЫ УЖЕ ЗНАЕМ О КЛИЕНТЕ:\n{context_memory}\n\n"
        if style_profile:
            context += f"СТИЛЬ ОБЩЕНИЯ КЛИЕНТА:\n{style_profile}\n\n"
            
        return FOLLOW_UP_PROMPT_TEMPLATE.format(
            context=context, 
            conversation_history=history_text,
            days_since_last_message=days_since_last_message,
            last_message=last_message or "Последнее сообщение не сохранено"
        )

    @staticmethod
    def build_analysis_prompt(history_text: str, current_profile: str = "", current_memory: str = "") -> str:
        """Промпт для анализа стиля и накопления знаний."""
        return f"""
Проанализируй диалог и обнови профиль клиента.
Текущий профиль стиля: {current_profile}
Текущие знания о проекте: {current_memory}

ИСТОРИЯ ДИАЛОГА:
{history_text}

Выдай результат в формате JSON:
{{
  "style_profile": "краткое описание стиля (формальный/нет, краткий/подробный, смайлы и т.д.)",
  "context_memory": "ключевые факты о проекте, задачах, предпочтениях клиента"
}}
Отвечай ТОЛЬКО чистым JSON.
"""

    @staticmethod
    def build_outreach_prompt(
        vacancy_text: str,
        specialization: str,
        case_data: Optional[dict] = None
    ) -> str:
        from core.config.prompts import OUTREACH_PROMPT_TEMPLATE
        
        case_info = "Кейсы не найдены, опирайся на свой общий экспертный опыт."
        if case_data and case_data.get('case_found'):
            cd = case_data['case_data']
            case_info = f"Проект: {cd['title']}\n"
            case_info += f"Описание: {cd['short_description']}\n"
            case_info += f"Результаты: {cd.get('results', {}).get('metric_1', '')}, {cd.get('results', {}).get('metric_2', '')}"
            
        return OUTREACH_PROMPT_TEMPLATE.format(
            vacancy_text=vacancy_text,
            specialization=specialization,
            case_info=case_info
        )

# Singleton
prompt_builder = PromptBuilder()

