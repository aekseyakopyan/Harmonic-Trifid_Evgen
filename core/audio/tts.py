
import asyncio
import os
import edge_tts
from core.utils.logger import logger

class TextToSpeech:
    """
    Синтез речи с использованием Microsoft Edge TTS (бесплатно и качественно).
    """
    def __init__(self):
        # Голос: ru-RU-DmitryNeural (мужской) или ru-RU-SvetlanaNeural (женский)
        self.voice = "ru-RU-DmitryNeural" 
        self.output_dir = "downloads/tts"
        os.makedirs(self.output_dir, exist_ok=True)

    async def speak(self, text: str, filename: str = None) -> str:
        """
        Преобразует текст в аудиофайл.
        Возвращает путь к файлу.
        """
        if not text:
            return None
            
        if not filename:
            import uuid
            filename = f"{uuid.uuid4()}.mp3"
            
        file_path = os.path.join(self.output_dir, filename)
        
        try:
            logger.info(f"🗣️ Generating TTS for: {text[:30]}...")
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(file_path)
            logger.info(f"✅ TTS output saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ TTS generation failed: {e}")
            return None

# Глобальный экземпляр
tts_engine = TextToSpeech()
