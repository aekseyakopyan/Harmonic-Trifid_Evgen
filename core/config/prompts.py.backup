import os

def _load_prompt(filename: str) -> str:
    """Загружает текст промпта из базы знаний систем Евгения."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Указываем путь к папке в системах Евгения (папка пока называется alexey для совместимости)
    path = os.path.join(base_dir, "systems", "alexey", "knowledge_base", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Ошибка при загрузке промпта {filename}: {e}")
        # Фолбек на старое место, если в новом нет
        fallback_path = os.path.join(base_dir, "prompts", filename)
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            return ""

# Загружаем промпты из файлов
SYSTEM_PROMPT = _load_prompt("system_prompt.md")
USER_PROMPT_TEMPLATE = _load_prompt("user_prompt.md")
FOLLOW_UP_PROMPT_TEMPLATE = _load_prompt("follow_up_prompt.md")
OUTREACH_PROMPT_TEMPLATE = _load_prompt("outreach_prompt.md")

# Варианты эмоциональных состояний (подробные описания из knowledge_base)
EMOTIONS = {
    "interested": "заинтересован (видишь потенциал в проекте, готов давать идеи)",
    "skeptical": "скептичен (новое лицо, нужно убедиться в серьезности)",
    "irritated": "слегка раздражен (шаблоны, игнор советов, требования невозможного)",
    "tired": "устал (похожие вопросы, затянувшийся диалог)",
    "intrigued": "заинтригован (нестандартная задача, умный вопрос)",
    "uncertain": "не уверен (вне экспертизы, нужно больше данных)"
}


