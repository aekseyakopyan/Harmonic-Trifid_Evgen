import sqlite3
import os
import re

def get_emoji_count(text):
    if not text: return 0
    return len(re.findall(r"[\U00010000-\U0010ffff]", text))

def cleanup_spam():
    databases = [
        ("data/db/history_buyer_leads.db", "history_leads"),
        ("data/db/all_historical_leads.db", "historical_leads"),
        ("data/db/vacancies.db", "vacancies")
    ]
    
    # Очень широкие паттерны для удаления продавцов и спама
    spam_keywords = [
        "kwork", "кворк", "монтажер", "монтаж роликов", "ютуб", "youtube",
        "меня зовут", "сертифицированный", "сделаю чат", "аудит безопасности",
        "создам для вас", "карточки для мп", "кому нужны клиенты", "всех приветствую",
        "создаю сайты", "привет, меня зовут", "продюсер", "продюссер",
        "художник", "2d артист", "2d artist", "иллюстратор",
        "помощник", "ассистент", "автор", "редактор", "ии-текст",
        "#помогу", "#услуги", "бизнесассистент", "беру проект", "занимаюсь составлением", "могу помочь с",
        "сценарист", "администратор", "smm", "смм", "#маркетолог",
        "техспец", "куратор", "менеджер по продажам", "sales manager", "эксперт", "#резюме", "#ищуработу",
        "занимаюсь составлением", "сертифицированный", "коллеги", "возьму в работу", "татьяна мелехова",
        "оптимизированных описаний", "системные продажи", "полное сопровождение", "вернуть себе время",
        "маркетинговой стратегии", "пишу тексты", "напишу текст", "копирайтер", "дизайнер",
        "хочу предложить", "ищу заказы", "ищу подработоку", "ищу работу", "в поиске проектов",
        "аккаунт в авито", "написания отзывов", "женский аккаунт", "мужской аккаунт",
        "аккаунты авито с отзывами", "положительными отзывами",
        "маркетинговое агентство", "маркетинговом агентстве", "event-агентство", "посевы", "посевам",
        "короткие ролики", "коротких роликов", "рилс", "reels", "shorts",
        "клонировать голос", "клонирование голоса",
        "вебинар", "АСУТП", "таргетолог", "таргет", "facebook", "instagram", "фейсбук", "инстаграм", "таргетированная"
    ]
    
    # Регулярки для более точного удаления
    spam_regex = [
        r"ищ(?:у|ем)\s+(?:работу|заказы|проекты|клиентов|подработку)",
        r"возьму.{0,10}работу",
        r"сертифицированн",
        r"меня\s+зовут.{0,20}[А-Я]",
        r"помогу.{0,20}(?:продажами|продвижением|маркетингом)",
        r"коллеги,.{0,20}(?:кто\s+хочет|устали|хочу)"
    ]

    for db_path, table_name in databases:
        if not os.path.exists(db_path):
            print(f"⚪ Пропуск: {db_path} (не найден)")
            continue
            
        print(f"⏳ Очистка {db_path} (таблица {table_name})...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Получаем колонки
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'text' not in columns:
                # Пытаемся найти альтернативную таблицу
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                all_tables = [t[0] for t in cursor.fetchall()]
                found_table = False
                for t in all_tables:
                    cursor.execute(f"PRAGMA table_info({t});")
                    cols = [c[1] for c in cursor.fetchall()]
                    if 'text' in cols:
                        table_name = t
                        columns = cols
                        found_table = True
                        break
                if not found_table:
                    print(f"  ❌ Не удалось найти таблицу с текстом в {db_path}")
                    conn.close()
                    continue

            # Читаем все записи для фильтрации в Python (для корректной работы с кириллицей)
            cursor.execute(f"SELECT id, text FROM {table_name}")
            rows = cursor.fetchall()
            
            ids_to_delete = []
            for row_id, text in rows:
                if not text: continue
                text_lower = text.lower()
                
                is_spam = False
                
                # 1. Проверка по ключевым словам
                for kw in spam_keywords:
                    if kw.lower() in text_lower:
                        is_spam = True
                        break
                
                # 2. Проверка по регуляркам
                if not is_spam:
                    for pattern in spam_regex:
                        if re.search(pattern, text, re.IGNORECASE):
                            is_spam = True
                            break
                
                # 3. Проверка на избыток эмодзи
                if not is_spam:
                    if get_emoji_count(text) > 8:
                        is_spam = True
                
                if is_spam:
                    ids_to_delete.append(row_id)
            
            if ids_to_delete:
                # Удаляем пачками по 500 штук
                total_deleted = 0
                for i in range(0, len(ids_to_delete), 500):
                    batch = ids_to_delete[i:i+500]
                    placeholders = ','.join(['?'] * len(batch))
                    cursor.execute(f"DELETE FROM {table_name} WHERE id IN ({placeholders})", batch)
                    total_deleted += cursor.rowcount
                
                conn.commit()
                print(f"  ✅ Удалено записей: {total_deleted}")
            else:
                print("  ✅ Спам не обнаружен.")
                
            conn.close()
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

if __name__ == "__main__":
    cleanup_spam()
