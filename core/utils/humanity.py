import asyncio
import random
import re
from typing import List

class HumanityManager:
    """
    Manages human-like communication parameters and behaviors.
    """

    def __init__(self):
        # Characters per minute (avg human: 200-300)
        self.cpm_range = (220, 320)
        # Seconds per 100 chars for reading
        self.reading_speed_per_100 = (1.2, 2.0)
        # Pause between chunks (seconds)
        self.chunk_pause = (0.8, 2.2)
        # Max chance to split a message into parts (0.0 to 1.0)
        self.split_chance = 0.15

    def get_reading_delay(self, text: str) -> float:
        """Calculates how long it takes to 'read' a message."""
        char_count = len(text)
        delay_per_100 = random.uniform(*self.reading_speed_per_100)
        return (char_count / 100.0) * delay_per_100

    def get_typing_duration(self, text: str) -> float:
        """Calculates typing duration based on text length and CPM."""
        cpm = random.uniform(*self.cpm_range)
        duration = (len(text) / cpm) * 60.0
        # Add some randomness (jitter)
        return duration * random.uniform(0.9, 1.1)

    def split_into_human_chunks(self, text: str) -> List[str]:
        """
        Sometimes splits text into multiple messages for a more human feel.
        e.g., 'Hi! [Pause] How are you?' instead of one message.
        """
        # 1. Clean up triple backticks blocks - don't split inside them
        # (For now, let's just split by paragraphs as chunks)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # 2. Logic to decide if we want to split the first sentence
        # Only if the first paragraph is short and we hit the random chance
        if len(paragraphs) > 0 and random.random() < self.split_chance:
            first_p = paragraphs[0]
            sentences = re.split(r'(?<=[.!?])\s+', first_p)
            if len(sentences) > 1 and len(sentences[0]) < 50:
                # Split first sentence into its own chunk
                hook = sentences[0]
                remainder = " ".join(sentences[1:])
                paragraphs = [hook, remainder] + paragraphs[1:]
        
        return paragraphs

    async def simulate_typing(self, client, chat_id, text: str, action='typing'):
        """Simulates the 'typing' status for a realistic duration."""
        duration = self.get_typing_duration(text)
        async with client.action(chat_id, action):
            await asyncio.sleep(duration)

humanity_manager = HumanityManager()
