import threading
from collections import deque

class HandoverManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(HandoverManager, cls).__new__(cls)
                # deque with maxlen automatically evicts the OLDEST entries (insertion order preserved)
                cls._instance.automated_msg_ids = deque(maxlen=1000)
        return cls._instance

    def mark_as_automated(self, msg_id: int):
        self.automated_msg_ids.append(msg_id)

    def is_automated(self, msg_id: int) -> bool:
        return msg_id in self.automated_msg_ids

handover_manager = HandoverManager()
