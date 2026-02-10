# СТРУКТУРИРОВАННАЯ БАЗА ДАННЫХ: B2B Sales Communication Framework

**Предназначена для:** обучения ИИ-моделей, создания чат-ботов, автоматизации коммуникации  
**Версия:** 1.0 (Февраль 2026)  
**Язык:** русский  
**Источник:** Виталий Говорухин + CRM Chat + практический опыт

---

## РАЗДЕЛ 1: ЯДРО КОММУНИКАЦИИ

### 1.1 Три столпа успеха

```yaml
PILLARS:
  1_PERSONALIZATION:
    definition: "Персонализация под конкретную боль клиента, не компанию"
    levels: ["zero", "industry", "company"]
    impact: "Increases reply rate from 5% → 15-25%"
    
  2_SPEED:
    definition: "Скорость ответа как конкурентное преимущество"
    optimal_time: "5-15 minutes"
    impact: "First responder gets 60% higher conversion"
    
  3_SYSTEMATIZATION:
    definition: "Скрипты, чеклисты, метрики, постоянная оптимизация"
    components: ["scripts", "checklists", "CRM", "analytics"]
    impact: "Scales team from 1 to 100+ outreach per day"
```

### 1.2 Базовые аксиомы

```yaml
AXIOMS:
  axiom_1: "Продавайте так, чтобы клиент вернулся за следующей покупкой"
    corollary: "Этичные продажи = долгосрочные отношения"
    
  axiom_2: "Общайтесь там, где удобно клиенту"
    corollary: "Если написал в WhatsApp → ответьте в WhatsApp, не отправляйте на сайт"
    
  axiom_3: "Клиент не знает что купить до диалога"
    corollary: "Сначала вопросы о потребности, потом цена"
    
  axiom_4: "Инициатива всегда должна исходить от продавца"
    corollary: "Если клиент сказал 'подумаю' → назначьте конкретное время следующего контакта"
    
  axiom_5: "Дороговизна vs выгода зависит от контекста"
    corollary: "Объясняйте не почему дорого, а в чем разница между вариантами"
```

---

## РАЗДЕЛ 2: КЛАССИФИКАЦИЯ СООБЩЕНИЙ

### 2.1 По стадии коммуникации

```yaml
STAGES:
  
  COLD_OUTREACH:
    purpose: "Привлечь внимание холодного контакта"
    length: "50-100 (Telegram) / 100-150 (WhatsApp)"
    must_include: 
      - specific_name
      - source_mention
      - pain_point
      - concrete_result
      - soft_cta
      - opt_out_option
    tone: "разговорный (Telegram) / профессиональный (WhatsApp)"
    success_metric: "15-25% reply rate"
    
  NEED_DISCOVERY:
    purpose: "Выяснить конкретные потребности"
    key_action: "Задавай вопросы, не отправляй прайс"
    pattern: "Что → Зачем → Когда → Бюджет"
    tone: "интересующийся, слушающий"
    success_metric: "Получить конкретные ответы на 4 вопроса"
    
  OBJECTION_HANDLING:
    purpose: "Нейтрализовать возражение, удержать интерес"
    pattern: "Выслушай → Уточни → Аргументируй → Закрой"
    tone: "эмпатичный, понимающий"
    key_rule: "Не защищайся, объясняй разницу"
    success_metric: "Либо ответ 'да', либо четкое 'нет'"
    
  CLOSING:
    purpose: "Закрыть сделку, назначить встречу/оплату"
    key_action: "Конкретное действие (встреча/счет) + конкретный дедлайн"
    tone: "уверенный, позитивный"
    success_metric: "Встреча назначена или счет отправлен"
    
  FOLLOW_UP:
    purpose: "Напомнить о себе, пробить 'подумаю'"
    rule: "Каждое касание = НОВАЯ информация, не повтор"
    spacing: "3-4 дня между касаниями, максимум 3-4 касания"
    tone: "деловой, вежливый"
    success_metric: "Либо согласие, либо явный отказ"
```

### 2.2 По типу возражения

```yaml
OBJECTIONS:

  TOO_EXPENSIVE:
    client_says: ["Дорого", "Ищу дешевле", "Скидка есть?"]
    algorithm:
      step_1: "Выслушать: 'Я понимаю'"
      step_2: "Уточнить: 'В пределах какой суммы планировали?'"
      step_3: "Аргументировать: 'Разница между вариантами такая...'"
      step_4: "Закрыть: 'Подходит?'"
    antipattern: "НЕ защищать цену"
    response_template: "Не 'это не дорого', а 'вот почему вариант дороже имеет смысл'"
    
  NEED_TO_THINK:
    client_says: ["Подумаю", "Нужно время", "Обсужу с боссом"]
    algorithm:
      step_1: "Согласиться: 'Совершенно верно, важно обдумать'"
      step_2: "Уточнить: 'Когда ты сможешь в этом разобраться?'"
      step_3: "Назначить дату: 'Я напишу завтра в 10:00'"
      step_4: "Соблюдать дату: именно в 10:00, не раньше, не позже"
    key_rule: "Назначь конкретное время, не жди инициативы клиента"
    
  NOT_INTERESTED:
    client_says: ["Не интересует", "Неактуально", "Не нам"]
    algorithm:
      step_1: "Спросить: 'Что не подошло?'"
      step_2: "Слушать ответ
      step_3: "Предложить: 'Может быть, в другой момент будет интересно'"
      step_4: "Добавить в 'холодную базу' на 6 месяцев"
    key_rule: "Честное нет лучше неопределенности"
    
  COMPARING_WITH_COMPETITOR:
    client_says: ["А у конкурента дешевле", "Вот он предлагает..."]
    algorithm:
      step_1: "Не критиковать конкурента"
      step_2: "Спросить: 'Что именно в их предложении привлекает?'"
      step_3: "Найти свое преимущество"
      step_4: "Предложить: 'Может быть, это два совсем разных решения?'"
    key_rule: "Не спор, а понимание потребности"
```

---

## РАЗДЕЛ 3: ШАБЛОНЫ И СКРИПТЫ

### 3.1 Структурированные шаблоны

```yaml
TEMPLATE_FIRST_MESSAGE_TELEGRAM:
  structure:
    line_1: "[NAME]. Нашел тебя в [SOURCE]."
    line_2: "Видел, что [PAIN_POINT]. Помогли похожим [RESULT] за [TIME]."
    line_3: "[SOFT_CTA]?"
    line_4: "P.S. если неактуально → напиши 'стоп'"
  
  replacements:
    "[NAME]": "real_person_name_only"
    "[SOURCE]": "specific_group_or_profile"
    "[PAIN_POINT]": "exact_problem_mentioned"
    "[RESULT]": "specific_metric_with_number"
    "[TIME]": "timeframe_days_or_weeks"
    "[SOFT_CTA]": "question_form_only"
  
  validation:
    word_count: "50-100"
    ends_with: "question"
    includes_opt_out: true
    tone: "casual_russian"
    
TEMPLATE_FIRST_MESSAGE_WHATSAPP:
  structure:
    greeting: "Здравствуйте, [NAME]."
    intro: "Я [MANAGER_NAME] из [COMPANY]. Помогаем [TARGET_AUDIENCE] [SOLVE_PROBLEM]."
    proof: "Недавно [CONCRETE_CASE] и удалось [RESULT]."
    ask: "Было бы интересно обсудить вашу ситуацию? [TIME_REQUIRED]."
    opt_out: "Если неактуально → просто не отвечайте."
  
  validation:
    word_count: "100-150"
    tone: "professional_formal"
    ends_with: "question"
    includes_proof: true

TEMPLATE_PRICE_QUESTION:
  step_1_intercept:
    dont_say: "Вот наш прайс"
    say: "Зависит от ваших задач"
  step_2_questions:
    ask_1: "Какую конкретно проблему вы хотите решить?"
    ask_2: "На какой срок ищете решение?"
    ask_3: "Примерный бюджет есть?"
  step_3_offer:
    show_variants: "exactly_2_not_more"
    explain_difference: "benefits_not_price"
  step_4_close:
    action: "Договорились?"

TEMPLATE_OBJECTION_EXPENSIVE:
  step_1: "Понимаю полностью."
  step_2: "Скажи, в пределах какой суммы планировал?"
  step_3_client_answer: "[RECEIVED_AMOUNT]"
  step_4_offer: "Есть вариант '[VARIANT_NAME]' за [AMOUNT]"
  step_5_explain: "Более дорогой вариант добавляет [BENEFIT_1], [BENEFIT_2], [BENEFIT_3]"
  step_6_clarify: "Что для тебя критичнее: [OPTION_A] или [OPTION_B]?"
  step_7_close: "[NEXT_ACTION]"
```

### 3.2 Готовые примеры по вертикалям

```yaml
VERTICAL_SAAS_TECHNICAL:
  target_position: "CTO, Lead Engineer, DevOps"
  pain_points:
    - "Database latency"
    - "Scalability issues"
    - "Infrastructure costs"
  sample_first_message: |
    Привет, [Name]. Нашел тебя в группе DevOps Engineers.
    
    Видел твой пост про масштабирование БД. Помогли 3 похожим 
    стартапам сократить время запроса на 60%.
    
    Стоит ли обсудить твою ситуацию?
  
  sample_objection_response: |
    Скажу честно: вариант дешевле работает медленнее. 
    Если скорость критична → нужен дороже. 
    Если бюджет первичен → дешевле подойдет. 
    Что для вас приоритет?

VERTICAL_MARKETING_GROWTH:
  target_position: "Growth Manager, Marketing Manager, CMO"
  pain_points:
    - "Low conversion rate"
    - "High CAC"
    - "Churn issues"
  sample_first_message: |
    Привет, [Name]. Вижу тебя активным в Growth Hacking группе.
    
    На днях помогли похожему SaaS увеличить conversion на 35% за 60 дней.
    
    Может быть интересно? Есть готовый кейс.

VERTICAL_FINANCE_INVESTMENT:
  target_position: "Investment Manager, CFO, Finance Director"
  pain_points:
    - "Portfolio optimization"
    - "Risk management"
    - "Regulatory compliance"
  sample_first_message: |
    Привет, [Name]. Вспомнил о тебе после новости что вы 
    закрыли раунд Series B.
    
    Поздравляю! На этом этапе часто встает задача с 
    портфельной оптимизацией. Помогли похожему фонду найти 
    дополнительный доход в портфеле.
    
    Обсудим?
```

---

## РАЗДЕЛ 4: ПРАВИЛА И КОНСТРЕЙНТЫ

### 4.1 Hard Rules (нарушение = провал)

```yaml
HARD_RULES:
  
  rule_1_personal_name:
    statement: "Всегда используй реальное имя контакта"
    violation: "Привет! / Здравствуйте!"
    penalty: "Классифицируется как спам, высокий bounce"
    
  rule_2_source_specific:
    statement: "Всегда упомяни конкретный источник"
    violation: "Общее письмо без указания откуда нашел"
    penalty: "Клиент не верит, что это не массовая рассылка"
    
  rule_3_concrete_pain:
    statement: "Боль должна быть конкретной, не отвлеченной"
    violation: "Помогаем компаниям расти" vs "Видел пост про масштабирование БД"
    penalty: "Низкий reply rate, кажется не для него"
    
  rule_4_result_with_metrics:
    statement: "Результат ВСЕГДА с конкретной цифрой или %"
    violation: "Помогли много / помогли улучшить"
    correct: "сокращение на 60% / в 3 раза выше / 35% за 60 дней"
    penalty: "Невпечатляющее, клиент проходит мимо"
    
  rule_5_soft_cta_first_message:
    statement: "Первое сообщение = мягкий вопрос, НЕ требование встречи"
    violation: "Давайте созвонимся завтра в 14:00"
    correct: "Обсудим? / Может быть интересно?"
    penalty: "Клиент видит давление, удаляет чат"
    
  rule_6_response_time:
    statement: "Ответ на входящее сообщение = 5-15 минут рабочего времени"
    violation: "Ответить через час, день, неделю"
    penalty: "Клиент уже договорился с конкурентом"
    
  rule_7_two_variants_max:
    statement: "При предложении цены = МАКСИМУМ 2 варианта"
    violation: "Есть еще 5 других опций"
    penalty: "Паралич анализа, клиент не принимает решение"
    
  rule_8_one_channel_first:
    statement: "Общайтесь в ПЕРВОМ канале куда написал клиент"
    violation: "Ответить в другом мессенджере, отправить на сайт"
    penalty: "Клиент раздражен, закрывает"
```

### 4.2 Soft Guidelines (нарушение = низкая эффективность)

```yaml
SOFT_GUIDELINES:
  
  guideline_1_word_count:
    telegram: "50-100 слов"
    whatsapp: "100-150 слов"
    penalty_low: "не читают полностью"
    penalty_high: "стена текста, скипают"
    
  guideline_2_tone:
    telegram: "Casual, разговорный, неформальный, ты-форма"
    whatsapp: "Professional, деловой, вы-форма, более формален"
    penalty: "Несоответствие = странно читать"
    
  guideline_3_sending_time:
    ideal: "Вт-Чт, 10:00-16:00 по часовому поясу клиента"
    avoid_pn: "Пн = полный календарь, Пт = спешка"
    avoid_times: "Выходные, праздники, ночь (2-6 часов)"
    penalty: "Сообщение теряется в потоке"
    
  guideline_4_follow_up_spacing:
    first_to_second: "3-5 дней"
    second_to_third: "3-4 дня"
    third_to_fourth: "3-4 дня"
    max_touches: "3-4 касания, потом 6 месяцев пауза"
    
  guideline_5_every_message_question:
    statement: "Каждое сообщение менеджера заканчивается вопросом"
    benefit: "Форс действия, инициатива остается у менеджера"
    
  guideline_6_no_voice_messages:
    statement: "Основная информация = письменно, не голосом"
    exception: "Голосовые только как дополнение к тексту"
    reason: "Люди не слушают в мессенджере"
```

---

## РАЗДЕЛ 5: МЕТРИКИ И KPI

```yaml
METRICS:
  
  reply_rate:
    definition: "% контактов которые ответили на первое сообщение"
    poor: "<10%"
    good: "15-25%"
    excellent: ">25%"
    how_to_improve: "Улучши персонализацию, конкретность болей"
    
  time_to_first_reply:
    definition: "Как быстро клиент ответил на первое сообщение"
    optimal: "5-15 минут"
    acceptable: "15-60 минут"
    poor: ">1 часа"
    implication: "Быстрый ответ = высокий интерес"
    
  conversion_reply_to_meeting:
    definition: "% из ответивших кто согласился на встречу"
    poor: "<15%"
    good: "20-40%"
    excellent: ">40%"
    how_to_improve: "Лучшая квалификация в диалоге, правильные вопросы"
    
  response_time_in_dialogue:
    definition: "Скорость ответа менеджера на сообщение клиента"
    optimal: "2-5 минут"
    good: "5-15 минут"
    acceptable: "15-60 минут"
    impact: "каждая минута задержки = снижение конверсии"
    
  follow_up_rate:
    definition: "% из потенциальных клиентов кто получил follow-up"
    target: "70%+ на следующий день"
    importance: "Без follow-up = 80% потерь"
    
  deal_close_rate:
    definition: "% из встреч которые привели к сделке"
    typical_range: "20-40% в зависимости от чека"
    improving: "Зависит больше от скрипта переговоров, чем от аутрича"
```

---

## РАЗДЕЛ 6: ИНТЕГРАЦИЯ С ИИ

### 6.1 Input Parameters для ИИ

```yaml
INPUT_SCHEMA:
  
  prospect:
    type: "object"
    required: ["first_name", "position", "company"]
    optional: ["last_name", "company_size", "industry"]
    example:
      first_name: "Sergey"
      last_name: "Petrov"
      position: "Lead DevOps Engineer"
      company: "TechCorp"
      company_size: "25-50"
      industry: "SaaS"
  
  outreach_context:
    type: "object"
    required: ["channel", "stage", "source", "pain_point", "value_prop"]
    optional: ["social_proof", "urgency", "budget_known"]
    example:
      channel: "telegram"
      stage: "first_contact"
      source: "DevOps Engineers group"
      pain_point: "Database latency causing 5+ second query times"
      value_prop: "60% reduction in query time"
      social_proof: ["3 similar SaaS companies", "ROI 150% in 3 months"]
      urgency: "high"
      budget_known: false
  
  constraints:
    type: "object"
    required: ["word_count_min", "word_count_max", "tone", "language"]
    example:
      word_count_min: 50
      word_count_max: 100
      tone: "casual"
      language: "russian"
      cta_type: "question"
      must_include: ["personal_name", "source", "specific_pain", "concrete_result", "opt_out"]
      must_avoid: ["generic_phrases", "pressure_language", "features_not_benefits"]
```

### 6.2 Output Validation для ИИ

```yaml
OUTPUT_VALIDATION:
  
  checklist:
    personal_name: "Используется реальное имя (не 'Привет')"
    source_mention: "Упомянут конкретный источник"
    pain_specific: "Боль конкретизирована, не обобщена"
    result_metric: "Результат с цифрой/процентом"
    word_count: "Соответствует диапазону"
    ends_with_question: "Заканчивается вопросом"
    opt_out_option: "Есть опция отказа"
    tone_match: "Тон соответствует каналу"
    no_spam_words: "Без спам-слов"
    
  scoring:
    full_match: "Все пункты ✓ → 100% = ГОТОВО"
    good: "8/9 пункта → 80%+ = хорошо"
    acceptable: "7/9 пункта → 70%+ = допустимо"
    poor: "<7 пункта → <70% = требует доработки"
    
  auto_reject_if:
    - "Generic greeting without name"
    - "Generic pain without specifics"
    - "No concrete result/metric"
    - "Word count out of range"
    - "No opt-out option"
```

---

## РАЗДЕЛ 7: ПРИМЕРЫ ПОЛНЫХ ДИАЛОГОВ

```yaml
EXAMPLE_1_SUCCESSFUL_FLOW:
  title: "Cold Contact → Meeting (3 часа)"
  day: 1
  time: "11:00"
  speaker: "MANAGER"
  message: |
    Привет, Сергей. Нашел тебя в группе DevOps Engineers.
    Видел твой пост про масштабирование БД.
    Помогли 3 похожим стартапам сократить время запроса на 60%.
    Стоит ли обсудить твою ситуацию?
    P.S. если неактуально → напиши "стоп"
  
  action_analysis: |
    ✓ Personal name: Sergey
    ✓ Source: DevOps Engineers group
    ✓ Specific pain: database scaling
    ✓ Concrete result: 60% reduction
    ✓ Soft CTA: question form
    ✓ Opt-out: P.S. "stop"
    ✓ Word count: 65 words (optimal)
    ✓ Tone: casual Russian
  
  expected_result: "15-25% reply rate"
  
  timeline:
    "11:15": "Client replies 'interested, tell more'"
    "11:20": "Manager lists 3 benefits with specifics"
    "11:45": "Client asks 'how much?'"
    "11:50": "Manager asks discovery questions (not price)"
    "12:10": "Client provides context (DB size, budget)"
    "12:15": "Manager offers 2 variants, asks choice"
    "12:35": "Client picks option + time slot"
    "12:40": "Manager confirms, sends Zoom link, thanks client"
  
  result: "Meeting booked in 1.5 hours"
  conversion_rate: "100% (cold contact → meeting)"
```

---

## РАЗДЕЛ 8: Ошибки и Антипаттерны

```yaml
ANTIPATTERN_1_GENERIC_OPENING:
  wrong: "Привет! / Здравствуйте! / Добрый день!"
  right: "Привет, [ИМЕЯ]."
  impact: "Распознается как массовая рассылка"
  fix: "ВСЕГДА используй реальное имя"

ANTIPATTERN_2_NO_SOURCE:
  wrong: "Вижу что вы работаете в [INDUSTRY]"
  right: "Нашел тебя в группе [GROUP_NAME]"
  impact: "Клиент не верит что это персонально ему"
  fix: "Упомяни КОНКРЕТНЫЙ источник"

ANTIPATTERN_3_GENERIC_PAIN:
  wrong: "Помогаем компаниям расти"
  right: "Видел твой пост про масштабирование БД"
  impact: "Может быть про любую компанию"
  fix: "Ссылайся на конкретную боль"

ANTIPATTERN_4_NO_RESULT_METRIC:
  wrong: "Помогли похожим компаниям улучшить результаты"
  right: "сократить время запроса на 60%"
  impact: "Невпечатляющее, скипают"
  fix: "ВСЕГДА показывай цифру"

ANTIPATTERN_5_WALL_OF_TEXT:
  wrong: "[100+ строк без разбиения]"
  right: "[3-5 строк, 2-3 абзаца]"
  impact: "Не читают в мессенджере"
  fix: "Максимум 100 слов (Telegram)"

ANTIPATTERN_6_PUSH_FOR_MEETING:
  wrong: "Давайте созвонимся завтра в 14:00"
  right: "Обсудим? / Может быть интересно?"
  impact: "Клиент видит давление, удаляет"
  fix: "Первое сообщение = мягкий вопрос"

ANTIPATTERN_7_IMMEDIATE_PRICE:
  wrong: "Вот наш прайс: [список цен]"
  right: "Зависит от ваших задач. Расскажите..."
  impact: "Клиент не видит персонального предложения"
  fix: "Сначала вопросы, потом цена"

ANTIPATTERN_8_TOO_MANY_OPTIONS:
  wrong: "У нас есть 5+ вариантов на выбор"
  right: "Есть вариант А (быстрее) или Б (дешевле)?"
  impact: "Паралич анализа, не принимают решение"
  fix: "Максимум 2 варианта"

ANTIPATTERN_9_NO_FOLLOW_UP:
  wrong: "Отправить первое письмо и ждать"
  right: "1е письмо → 3-5 дней → 2е письмо (НОВАЯ инфо)"
  impact: "80% потерь без follow-up"
  fix: "Минимум 3-4 касания в цепочке"

ANTIPATTERN_10_SLOW_RESPONSE:
  wrong: "Ответить на сообщение клиента через час"
  right: "Ответить через 5-15 минут"
  impact: "Каждая минута = снижение конверсии"
  fix: "Установите SLA (5-15 мин в рабочее время)"
```

---

## ЗАКЛЮЧЕНИЕ: ИСПОЛЬЗУЙ ЭТУ БАЗУ

Эта база создана для:

```
✓ Обучения новых менеджеров по продажам
✓ Создания AI-powered sales assistants
✓ Автоматизации холодного аутрича
✓ Оптимизации B2B коммуникации
✓ Валидации качества сообщений
✓ A/B тестирования вариантов
✓ Создания sales automation workflows
```

**Главное правило:** Начни с одного канала, овладей техникой на 100 контактах, потом масштабируй.

**Реалистичные результаты:**
- 100 первых сообщений → 15-25 ответов (15-25% reply rate)
- 15-25 ответов → 3-10 встреч (20-40% conversion)
- 3-10 встреч → 1-2 сделки (в зависимости от чека)

---

**Версия:** 1.0  
**Дата обновления:** Февраль 2026  
**Язык:** Russian  
**Качество для ИИ:** Production-ready
