
import time
import os
import re
import sys

# Пути к логам
HIST_LOG = "logs/parsers/history_run.log"
TODAY_LOG = "logs/parsers/today_run.log"
JOIN_LOG = "logs/parsers/chat_joiner.log"

TOTAL_ESTIMATED_MSGS = 2600000

def get_last_line(filepath):
    if not os.path.exists(filepath): return "Ожидание лога..."
    try:
        with open(filepath, 'rb') as f:
            f.seek(-200, 2) if os.path.getsize(filepath) > 200 else None
            last_line = f.readlines()[-1].decode('utf-8', errors='ignore').strip()
            return last_line
    except: return "Чтение..."

def parse_hist():
    if not os.path.exists(HIST_LOG): return 0, 0, 0
    with open(HIST_LOG, 'r', errors='ignore') as f:
        content = f.read()
    
    # Считаем общее кол-во из строк "DONE"
    done_msgs = sum(int(m) for m in re.findall(r'✅ Успешно: .+ \((\d+) сообщений\)', content))
    # Считаем текущие активные из строк "⏳"
    active_msgs = {}
    for match in re.finditer(r'\[(\d+)\] ⏳ .+: (\d+) сообщений', content):
        active_msgs[match.group(1)] = int(match.group(2))
    
    total = done_msgs + sum(active_msgs.values())
    leads = len(re.findall(r'INSERT OR IGNORE INTO history_leads', content)) # Или парсить итоговую строку
    return total, leads, len(active_msgs)

def parse_join():
    if not os.path.exists(JOIN_LOG): return 0, 0
    with open(JOIN_LOG, 'r', errors='ignore') as f:
        content = f.read()
    joined = len(re.findall(r'✅ Успешно вступил', content))
    already = len(re.findall(r'ℹ️ Вы уже состоите', content))
    return joined, already

def monitor():
    while True:
        os.system('clear')
        print("🚀 ЕДИНЫЙ МОНИТОРИНГ СИСТЕМЫ")
        print("="*60)
        
        # 1. МАШИНА ВРЕМЕНИ (2024-2026)
        h_msgs, h_leads, h_threads = parse_hist()
        h_perc = min(99.99, (h_msgs / TOTAL_ESTIMATED_MSGS) * 100) if TOTAL_ESTIMATED_MSGS else 0
        print(f"🕰️  МАШИНА ВРЕМЕНИ (2024-2026)")
        print(f"   Прогресс: {h_perc:5.2f}% [{'█'*int(h_perc/5)}{'░'*(20-int(h_perc/5))}]")
        print(f"   ✉️  Сообщений: {h_msgs:,} | 🎯 Лидов: {h_leads} | 🌊 Потоков: {h_threads}")
        print(f"   Последнее: {get_last_line(HIST_LOG)[:70]}")
        print("-" * 60)
        
        # 2. ЕЖЕДНЕВНЫЙ ПАРСЕР
        print(f"📅  ЕЖЕДНЕВНЫЙ МОНИТОРИНГ")
        t_line = get_last_line(TODAY_LOG)
        print(f"   Статус: {t_line[:70]}")
        print("-" * 60)
        
        # 3. ВХОД В ЧАТЫ
        j_count, a_count = parse_join()
        print(f"🤝  ВХОД В ЧАТЫ")
        print(f"   ✅ Новых: {j_count} | ℹ️ Уже в чате: {a_count}")
        j_line = get_last_line(JOIN_LOG)
        print(f"   Статус: {j_line[:70]}")
        print("="*60)
        print("Обновление каждую секунду. Ctrl+C для выхода.")
        
        time.sleep(1)

if __name__ == "__main__":
    try: monitor()
    except KeyboardInterrupt: pass
