import sys
import os
import time

# Добавляем корень проекта в path
sys.path.append(os.getcwd())

try:
    from systems.parser.tasks import process_lead_async
    import redis
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def check_redis():
    print("=== Проверка Redis ===")
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis доступен")
        return True
    except redis.ConnectionError:
        print("❌ Redis НЕ доступен. Celery не сможет работать.")
        return False

def test_enqueue():
    print("\n=== Тест: Отправка задачи в очередь ===")
    test_lead = {
        "text": "Нужен SEO-специалист для продвижения интернет-магазина. Бюджет до 100 000₽. Срочно!",
        "message_id": 999999,
        "chat_id": 123456789,
        "source": "test_channel",
        "timestamp": time.time()
    }
    
    try:
        # Отправка задачи
        task = process_lead_async.apply_async(
            args=[test_lead],
            priority=9
        )
        print(f"✅ Задача добавлена в очередь. ID: {task.id}")
        print("ℹ️  Чтобы увидеть результат, запустите worker: python3 main.py worker")
    except Exception as e:
        print(f"❌ Ошибка при отправке задачи: {e}")

if __name__ == "__main__":
    if check_redis():
        test_enqueue()
    else:
        print("\n⚠️  Запустите Redis (например, через Docker или brew install redis), чтобы протестировать Celery.")
