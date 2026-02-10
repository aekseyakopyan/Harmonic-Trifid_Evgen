import threading

class HandoverManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(HandoverManager, cls).__new__(cls)
                cls._instance.automated_msg_ids = set()
        return cls._instance

    def mark_as_automated(self, msg_id: int):
        self.automated_msg_ids.add(msg_id)
        # Очистка старых ID (оставляем последние 1000)
        if len(self.automated_msg_ids) > 1000:
            # Превращаем в список, срезаем и обратно в set
            self.automated_msg_ids = set(list(self.automated_msg_ids)[-1000:])

    def is_automated(self, msg_id: int) -> bool:
        return msg_id in self.automated_msg_ids

handover_manager = HandoverManager()
