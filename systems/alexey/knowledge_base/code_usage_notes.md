# Заметки по использованию в коде

## Краткие системные инструкции для конкретных задач

В коде `systems/alexey/tasks.py` используются короткие инструкции, которые дополняют основной промпт:

### Автоматический отклик (Outreach)
```python
# В функции run_automated_outreach
system_instr = """Ты - Алексей, пишешь первый отклик на вакансию. 
Будь конкретным, живым, без шаблонов. 
Покажи, что прочитал запрос. Не продавай - начни диалог."""
```

### Follow-ups (Напоминания)
```python
# В функции run_follow_ups
system_instr = """Ты - Алексей, пишешь напоминание клиенту.
Не дави, не обвиняй в молчании. 
Дай понять, что понимаешь занятость, но тема важная."""
```

### Ответ на входящее сообщение
```python
# В функции generate_response
system_instr = """Ты - Алексей, отвечаешь клиенту в переписке.
Подстраивайся под его стиль. Не повторяй то, что уже говорил.
Двигай диалог к цели, но без давления."""
```

---

## Рекомендации по имплементации

### Порядок промптов
1. **System prompt** (system_prompt.md) - базовая личность
2. **Краткая инструкция** (код выше) - контекст задачи
3. **User prompt** (user_prompt.md / outreach_prompt.md / follow_up_prompt.md) - конкретный запрос с данными

### Передача эмоционального состояния
```python
emotion_context = f"""ТЕКУЩЕЕ СОСТОЯНИЕ: {emotion}
({emotion_reason})"""

# Пример:
# ТЕКУЩЕЕ СОСТОЯНИЕ: interested
# (Клиент показал бюджет 300к и четкие сроки)
```

### Управление историей диалога
```python
# Не передавай всю историю - только релевантную часть
# Для ответа клиенту: последние 5-7 сообщений
# Для follow-up: последнее сообщение + ключевые моменты из диалога

def format_conversation_history(messages, max_messages=7):
    recent = messages[-max_messages:]
    return "\n".join([
        f"{'Клиент' if m.is_client else 'Алексей'}: {m.text}"
        for m in recent
    ])
```

### Детекция состояния
```python
def detect_emotion(conversation, client_message):
    """Определяет эмоциональное состояние на основе контекста"""
    
    # Первое сообщение
    if len(conversation) == 0:
        return "skeptical", "Первое сообщение от нового клиента"
    
    # Ключевые слова для интереса
    interest_signals = ["бюджет", "готовы начать", "когда можем", "сколько времени"]
    if any(signal in client_message.lower() for signal in interest_signals):
        return "interested", "Клиент показал серьезность намерений"
    
    # Повторяющиеся вопросы
    if is_repeated_question(client_message, conversation):
        return "tired", "Похожий вопрос уже обсуждали"
    
    # Дефолт
    return "interested", "Обычный диалог с потенциальным клиентом"
```

---

## Валидация ответов

### Проверка на "роботность"
```python
ROBOT_PHRASES = [
    "буду рад помочь",
    "не стесняйтесь обращаться",
    "позвольте предложить",
    "хотелось бы отметить",
    "давайте разберемся",
    "это отличный вопрос",
]

def check_robot_phrases(response):
    """Проверяет ответ на шаблонные фразы"""
    response_lower = response.lower()
    found = [phrase for phrase in ROBOT_PHRASES if phrase in response_lower]
    return found
```

### Проверка структуры
```python
def validate_response(response):
    """Базовая валидация ответа"""
    issues = []
    
    # Слишком много вопросов
    question_count = response.count("?")
    if question_count > 2:
        issues.append(f"Слишком много вопросов: {question_count}")
    
    # Слишком длинный
    if len(response) > 1000:
        issues.append("Ответ слишком длинный")
    
    # Эмодзи (запрещены)
    import re
    emoji_pattern = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)
    if emoji_pattern.search(response):
        issues.append("Обнаружены эмодзи")
    
    return issues
```

---

## Примеры использования

### Полный цикл генерации ответа
```python
async def generate_client_response(client_message, conversation, client_name, context):
    # 1. Определяем состояние
    emotion, emotion_reason = detect_emotion(conversation, client_message)
    
    # 2. Формируем историю
    history = format_conversation_history(conversation)
    
    # 3. Собираем промпт
    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context,
        user_name=client_name,
        query=client_message,
        conversation_history=history,
        current_emotion=f"{emotion}\n({emotion_reason})"
    )
    
    # 4. Генерируем
    response = await llm_client.generate(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt
    )
    
    # 5. Валидируем
    robot_phrases = check_robot_phrases(response)
    if robot_phrases:
        # Перегенерация или постобработка
        pass
    
    return response
```
