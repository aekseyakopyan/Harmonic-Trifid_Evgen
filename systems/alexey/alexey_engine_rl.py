"""Alexey Engine с RL оптимизацией."""
import asyncio
from typing import Dict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from systems.alexey.rl_agent import rl_agent
from core.utils.structured_logger import logger

class AlexeyEngineRL:
    """Alexey с Reinforcement Learning."""
    
    STRATEGY_PROMPTS = {
        'formal': "Стиль: Официальный, деловой. Обращение: 'Здравствуйте'. Тон: Профессиональный.",
        'casual': "Стиль: Дружеский, неформальный. Обращение: 'Привет'. Тон: Расслабленный.",
        'technical': "Стиль: Технический, с деталями. Много терминологии. Тон: Экспертный.",
        'consultative': "Стиль: Консультативный, вопросы. Тон: Заботливый, внимательный.",
        'direct': "Стиль: Кратко, без воды. Обращение: Простое. Тон: Прямолинейный."
    }
    
    async def generate_outreach_with_rl(self, lead_data: Dict) -> Dict:
        """Генерация отклика с RL выбором стратегии."""
        context = {
            'priority': lead_data.get('priority', 0),
            'budget': lead_data.get('budget', 0),
            'category': lead_data.get('category', 'unknown'),
            'tier': lead_data.get('tier', 'COLD')
        }
        
        strategy_id = await rl_agent.select_strategy(context)
        strategy_prompt = self.STRATEGY_PROMPTS[strategy_id]
        
        main_prompt = f"""
Ты — Алексей, опытный digital-маркетолог.

{strategy_prompt}

ЗАДАЧА КЛИЕНТА:
{lead_data.get('text', '')[:600]}

Напиши короткий отклик (2-3 предложения) в указанном стиле. БЕЗ эмодзи.
        """.strip()
        
        try:
            # Mock LLM response for testing
            message = f"[{strategy_id.upper()}] Здравствуйте! Готов помочь с вашим проектом. Опыт 5+ лет. Обсудим детали?"
            
            outreach_id = await rl_agent.record_outreach(
                lead_id=lead_data['id'],
                message=message,
                strategy_id=strategy_id,
                context=context
            )
            
            logger.info("outreach_generated_rl", lead_id=lead_data['id'], 
                       strategy=strategy_id, outreach_id=outreach_id)
            
            return {
                'message': message,
                'strategy_id': strategy_id,
                'outreach_id': outreach_id
            }
        except Exception as e:
            logger.error("outreach_generation_failed", error=str(e))
            raise
    
    async def record_client_reply(self, outreach_id: int, reply_received: bool,
                                  reply_time_seconds: int = None):
        """Зафиксировать ответ клиента."""
        await rl_agent.update_feedback(
            outreach_id=outreach_id,
            client_replied=reply_received,
            reply_time_seconds=reply_time_seconds
        )
    
    async def record_deal_closed(self, outreach_id: int, conversation_length: int,
                                deal_closed: bool, deal_amount: float = None):
        """Зафиксировать результат сделки."""
        await rl_agent.update_feedback(
            outreach_id=outreach_id,
            client_replied=True,
            conversation_length=conversation_length,
            deal_closed=deal_closed,
            deal_amount=deal_amount
        )

alexey_rl = AlexeyEngineRL()
