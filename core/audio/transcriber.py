
import os
import asyncio
import whisper
from core.utils.logger import logger
from core.config.settings import settings

class Transcriber:
    """
    Транскрибатор голосовых сообщений, использующий локальную модель OpenAI Whisper.
    Реализован как синглтон для загрузки модели один раз.
    """
    _instance = None
    _model = None
    _lock = None  # Created lazily after event loop starts (asyncio.Lock() at class level crashes Python 3.12+)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Transcriber, cls).__new__(cls)
        return cls._instance

    def _load_model(self):
        """Загрузка модели (синхронно, при первом использовании)."""
        if self._model is None:
            model_name = "small" # Оптимально для M1/M2/M3/M4
             # Можно вынести в настройки: settings.WHISPER_MODEL
            logger.info(f"⏳ Loading Whisper model '{model_name}'...")
            try:
                self._model = whisper.load_model(model_name)
                logger.info(f"✅ Whisper model '{model_name}' loaded successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to load Whisper model: {e}")
                raise

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """Lazy-init the lock so it is created inside a running event loop."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    async def transcribe(self, file_path: str) -> str:
        """
        Транскрибация аудиофайла.
        """
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return ""

        async with self._get_lock():
            try:
                # Загружаем модель в потоке, чтобы не блокировать event loop, если она ещё не загружена
                if self._model is None:
                    await asyncio.to_thread(self._load_model)
                
                logger.info(f"🎙️ Transcribing: {file_path}")
                
                # Запуск транскрибации в отдельном потоке
                result = await asyncio.to_thread(self._model.transcribe, file_path)
                text = result['text'].strip()
                
                logger.info(f"📝 Transcription result: {text}")
                return text
                
            except Exception as e:
                logger.error(f"❌ Transcription failed: {e}")
                return ""

# Глобальный экземпляр
transcriber = Transcriber()
