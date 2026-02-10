
import time
import os
import re
import sys

# Путь к логу исторического парсера
LOG_FILE = "logs/parsers/history_run.log"
TOTAL_ESTIMATED_MSGS = 2600000  # Примерная оценка для 2 лет

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_log():
    if not os.path.exists(LOG_FILE):
        return None
        
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        total_msgs = 0
        total_leads = 0
        active_chats = {}
        
        for line in lines:
            # Сбор количества сообщений
            # [1] ⏳ ChatName: 1000 сообщений...
            msg_match = re.search(r'\[\d+\] ⏳ .+: (\d+) сообщений', line)
            if msg_match:
                # В истории мы не можем просто суммировать, так как это периодические отчеты по каждому чату
                # Но для упрощения возьмем последнее число для каждого чата
                chat_id_match = re.search(r'\[(\d+)\]', line)
                if chat_id_match:
                    active_chats[chat_id_match.group(1)] = int(msg_match.group(1))
            
            # Завершенные чаты
            # [1] ✅ Успешно: ChatName (1234 сообщений)
            done_match = re.search(r'✅ Успешно: .+ \((\d+) сообщений\)', line)
            if done_match:
                total_msgs += int(done_match.group(1))
                # Удаляем из активных
                chat_id_match = re.search(r'\[(\d+)\]', line)
                if chat_id_match and chat_id_match.group(1) in active_chats:
                    del active_chats[chat_id_match.group(1)]

            # Лиды
            if "🏁 Финиш!" in line:
                finish_match = re.search(r'Найдено лидов: (\d+)', line)
                if finish_match:
                    total_leads = int(finish_match.group(1))
        
        # Суммируем текущие активные сообщения
        current_msgs = total_msgs + sum(active_chats.values())
        
        return {
            "total_msgs": current_msgs,
            "total_leads": total_leads,
            "active_tasks": len(active_chats)
        }
    except Exception as e:
        return None

def display():
    print("🕰️ МОНИТОРИНГ МАШИНЫ ВРЕМЕНИ (2024-2026)")
    print("------------------------------------------")
    
    while True:
        data = parse_log()
        
        if not data:
            sys.stdout.write("\r⏳ Ожидание данных из лога...")
        else:
            msgs = data['total_msgs']
            leads = data['total_leads']
            tasks = data['active_tasks']
            
            percent = (msgs / TOTAL_ESTIMATED_MSGS) * 100 if TOTAL_ESTIMATED_MSGS > 0 else 0
            if percent > 100: percent = 99.9 # Ограничение визуализации
            
            bar_len = 20
            filled = int(bar_len * percent / 100)
            bar = '█' * filled + '░' * (bar_len - filled)
            
            output = (
                f"\r📊 Прогресс: {percent:5.2f}% [{bar}] | "
                f"✉️ Сообщений: {msgs:,} | "
                f"🎯 Лидов: {leads} | "
                f"🌊 Потоков: {tasks}  "
            )
            sys.stdout.write(output)
            
        sys.stdout.flush()
        time.sleep(1)

if __name__ == "__main__":
    try:
        display()
    except KeyboardInterrupt:
        print("\n👋 Мониторинг остановлен.")
