"""
Reinforcement Learning агент для оптимизации стратегий откликов.
Использует Thompson Sampling (Multi-Armed Bandit).
"""

import asyncio
import aiosqlite
import numpy as np
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config.settings import settings
from core.utils.structured_logger import logger

class RLAgent:
    """RL агент с Thompson Sampling для выбора стратегий откликов."""
    
    def __init__(self):
        self.db_path = settings.VACANCY_DB_PATH
        self.strategies: Dict[str, Dict] = {}
        self.exploration_rate = 0.2  # 20% exploration
    
    async def load_strategies(self):
        """Загрузка параметров стратегий из БД."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT strategy_id, strategy_name, alpha, beta, 
                       total_attempts, successful_attempts, avg_reward
                FROM rl_strategies
            """)
            rows = await cursor.fetchall()
            
            for row in rows:
                self.strategies[row['strategy_id']] = {
                    'name': row['strategy_name'],
                    'alpha': row['alpha'],
                    'beta': row['beta'],
                    'total_attempts': row['total_attempts'],
                    'successful_attempts': row['successful_attempts'],
                    'avg_reward': row['avg_reward']
                }
    
    async def select_strategy(self, context: Dict) -> str:
        """Выбор стратегии через Thompson Sampling."""
        await self.load_strategies()
        
        # Exploration
        if np.random.random() < self.exploration_rate:
            strategy_id = np.random.choice(list(self.strategies.keys()))
            logger.info("rl_exploration", strategy=strategy_id)
            return strategy_id
        
        # Exploitation - Thompson Sampling
        sampled_rewards = {}
        for strategy_id, params in self.strategies.items():
            # Beta distribution sampling
            sample = np.random.beta(params['alpha'], params['beta'])
            
            # Context boost
            if context.get('category') == 'SEO' and strategy_id == 'technical':
                sample *= 1.2
            elif context.get('priority', 0) > 80 and strategy_id == 'direct':
                sample *= 1.1
            
            sampled_rewards[strategy_id] = sample
        
        best_strategy = max(sampled_rewards, key=sampled_rewards.get)
        logger.info("rl_exploitation", strategy=best_strategy)
        return best_strategy
    
    async def record_outreach(self, lead_id: int, message: str, 
                            strategy_id: str, context: Dict) -> int:
        """Записать отправленный отклик."""
        now = datetime.now()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO outreach_attempts 
                (lead_id, message_text, strategy_id, lead_priority, 
                 lead_budget, lead_category, time_of_day, day_of_week)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead_id, message, strategy_id,
                context.get('priority', 0),
                context.get('budget', 0),
                context.get('category', 'unknown'),
                now.hour, now.weekday()
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def update_feedback(self, outreach_id: int, client_replied: bool,
                            reply_time_seconds: Optional[int] = None,
                            conversation_length: int = 0,
                            deal_closed: bool = False,
                            deal_amount: Optional[float] = None):
        """Обновить feedback и параметры стратегии."""
        
        # Calculate reward
        reward = self._calculate_reward(
            client_replied, reply_time_seconds,
            conversation_length, deal_closed, deal_amount
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            # Update outreach
            await db.execute("""
                UPDATE outreach_attempts
                SET client_replied = ?, reply_time_seconds = ?,
                    conversation_length = ?, deal_closed = ?,
                    deal_amount = ?, reward = ?
                WHERE id = ?
            """, (client_replied, reply_time_seconds, conversation_length,
                  deal_closed, deal_amount, reward, outreach_id))
            
            # Get strategy_id
            cursor = await db.execute(
                "SELECT strategy_id FROM outreach_attempts WHERE id = ?",
                (outreach_id,)
            )
            strategy_id = (await cursor.fetchone())[0]
            
            # Update Thompson Sampling parameters
            success = 1.0 if reward > 0 else 0.0
            await db.execute("""
                UPDATE rl_strategies
                SET alpha = alpha + ?,
                    beta = beta + ?,
                    total_attempts = total_attempts + 1,
                    successful_attempts = successful_attempts + ?,
                    avg_reward = (avg_reward * total_attempts + ?) / (total_attempts + 1),
                    last_updated = CURRENT_TIMESTAMP
                WHERE strategy_id = ?
            """, (success, 1.0 - success, int(success), reward, strategy_id))
            
            await db.commit()
        
        logger.info("feedback_updated", outreach_id=outreach_id, 
                   strategy=strategy_id, reward=reward)
    
    def _calculate_reward(self, client_replied: bool,
                         reply_time_seconds: Optional[int],
                         conversation_length: int,
                         deal_closed: bool,
                         deal_amount: Optional[float]) -> float:
        """Расчет reward."""
        if not client_replied:
            return 0.0
        
        reward = 0.3  # Base for reply
        
        if reply_time_seconds and reply_time_seconds < 3600:
            reward += 0.1  # Fast reply
        
        if conversation_length >= 5:
            reward += 0.2
        elif conversation_length >= 3:
            reward += 0.1
        
        if deal_closed:
            reward += 1.0
            if deal_amount and deal_amount > 50000:
                reward += 0.5
            elif deal_amount and deal_amount > 20000:
                reward += 0.2
        
        return reward
    
    async def get_performance_report(self) -> Dict:
        """Отчет о производительности стратегий."""
        await self.load_strategies()
        
        report = {'strategies': {}, 'best_strategy': None, 'total_attempts': 0}
        best_reward = -1
        
        for strategy_id, params in self.strategies.items():
            report['strategies'][strategy_id] = {
                'name': params['name'],
                'total_attempts': params['total_attempts'],
                'success_rate': params['successful_attempts'] / max(params['total_attempts'], 1),
                'avg_reward': params['avg_reward'],
                'confidence': params['alpha'] / (params['alpha'] + params['beta'])
            }
            report['total_attempts'] += params['total_attempts']
            
            if params['avg_reward'] > best_reward and params['total_attempts'] > 10:
                best_reward = params['avg_reward']
                report['best_strategy'] = strategy_id
        
        return report

# Global instance
rl_agent = RLAgent()
