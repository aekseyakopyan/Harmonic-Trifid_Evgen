# Архитектура Harmonic Trifid

## Общее описание

**Harmonic Trifid** — комплексная B2B AI-система автоматизации продаж через Telegram.
Парсит лиды → фильтрует → генерирует отклики → ведёт диалоги → обучается.

---

## Схема компонентов

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HARMONIC TRIFID                                 │
│                                                                         │
│  ┌──────────────┐    ┌──────────────────────────────────────────────┐  │
│  │  Telegram    │    │              CORE (ядро)                     │  │
│  │  Channels /  │    │                                              │  │
│  │  Groups      │    │  ai_engine/        config/      database/   │  │
│  │              │    │  ├─ llm_client     ├─ settings  ├─ models   │  │
│  └──────┬───────┘    │  ├─ resilient_llm  └─ prompts   ├─ session  │  │
│         │            │  └─ prompt_builder              └─ connect  │  │
│         ▼            │                                              │  │
│  ┌──────────────┐    │  utils/            classifier/  audio/      │  │
│  │  PARSER      │    │  ├─ logger         ├─ intent    ├─ whisper  │  │
│  │  (systems/   │    │  ├─ health         └─ nlp_utils └─ tts      │  │
│  │   parser/)   │    │  ├─ smart_sender                            │  │
│  │              │    │  ├─ handover        knowledge_base/         │  │
│  │ 7-уровневый  │    │  ├─ llm_cache       ├─ retriever            │  │
│  │ пайплайн:    │    │  └─ humanity        ├─ web_searcher          │  │
│  │              │    │                     └─ proposals (43 файла) │  │
│  │ L0 normalize │    └──────────────────────────────────────────────┘  │
│  │ L1 hardblock │                                                       │
│  │ L2 dedup     │    ┌──────────────────────────────────────────────┐  │
│  │ L3 heuristic │    │              SYSTEMS                         │  │
│  │ L4 context   │    │                                              │  │
│  │ L5 ML (LR)   │───▶│  ┌────────────┐  ┌────────────────────────┐ │  │
│  │ L6 LLM deep  │    │  │  ALEXEY    │  │       GWEN             │ │  │
│  │              │    │  │ (userbot)  │  │  (supervisor bot)      │ │  │
│  │ entity_ext   │    │  │            │  │                        │ │  │
│  │ lead_scoring │    │  │ Pyrogram   │  │ aiogram / commands:    │ │  │
│  │ outreach_gen │    │  │ User API   │  │ /status /stats         │ │  │
│  └──────────────┘    │  │            │  │ /outreach /learn       │ │  │
│                      │  │ handlers/  │  │ /report /spam          │ │  │
│  ┌──────────────┐    │  │ tasks.py   │  │                        │ │  │
│  │  APPS        │    │  │ rl_agent   │  │ learning_engine        │ │  │
│  │              │    │  │ rate_lim   │  │ notifier               │ │  │
│  │ today_parser │    │  └────────────┘  └────────────────────────┘ │  │
│  │ chat_joiner  │    │                                              │  │
│  │ history_pars │    │  ┌─────────────────────────────────────────┐ │  │
│  │ unified_mon  │    │  │            DASHBOARD                    │ │  │
│  └──────────────┘    │  │  FastAPI :8000                          │ │  │
│                      │  │  /api/dashboard  /api/leads             │ │  │
│  ┌──────────────┐    │  │  /api/cases      /api/settings          │ │  │
│  │  SCRIPTS     │    │  │  /api/services   /api/parser            │ │  │
│  │ (48 утилит)  │    │  │  interface/ (HTML/CSS/JS + TWA)         │ │  │
│  │              │    │  └─────────────────────────────────────────┘ │  │
│  │ train_ml     │    └──────────────────────────────────────────────┘  │
│  │ seed_*       │                                                       │
│  │ backup       │    ┌──────────────────────────────────────────────┐  │
│  │ healthcheck  │    │         ИНФРАСТРУКТУРА                       │  │
│  └──────────────┘    │                                              │  │
│                      │  SQLite/PostgreSQL   Redis   Celery          │  │
│                      │  Ollama (local LLM)  OpenRouter (cloud)      │  │
│                      │  Docker / docker-compose                     │  │
│                      └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Поток данных (Data Flow)

```
Telegram Channels/Groups
        │
        ▼
  today_parser.py  ──→  7-уровневый фильтр  ──→  vacancies.db (SQLite)
        │                                              │
        │                                             HOT/WARM/COLD
        │                                              │
        │                              ┌───────────────┤
        │                              │               │
        ▼                              ▼               ▼
  chat_joiner.py            outreach_generator    GWEN notifier
  (вступление в            (черновик отклика)     (уведомление
   новые чаты)                    │                администратора)
                                  │
                    ┌─────────────┤  подтверждение / AUTO_OUTREACH
                    │             │
                    ▼             ▼
              ALEXEY userbot  Admin TG
              (отправка       (ручное
               отклика)        решение)
                    │
                    ▼
             Диалог с клиентом
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
    LLM response          Knowledge Base
    (DeepSeek →           (кейсы, FAQ,
     fallbacks)            предложения)
         │
         ▼
    smart_sender → MessageLog (SQLite)
         │
         ▼
    RL Agent (Thompson Sampling)
    адаптирует поведение на основе
    результатов диалогов
```

---

## Компоненты и файлы

| Компонент | Путь | Назначение |
|-----------|------|-----------|
| LLM Client | `core/ai_engine/llm_client.py` | OpenRouter + Ollama fallback |
| Circuit Breaker | `core/ai_engine/resilient_llm.py` | Защита от API outages |
| Конфигурация | `core/config/settings.py` | Pydantic settings из .env |
| Персона | `core/prompts/system_prompt.md` | 807 строк правил поведения |
| БД ORM | `core/database/models.py` | Lead, MessageLog, Case, Service, FAQ |
| Фильтр лидов | `systems/parser/lead_filter_advanced.py` | 7-уровневый пайплайн |
| Дедупликация | `systems/parser/duplicate_detector.py` | rubert embeddings + SequenceMatcher |
| ML классификатор | `systems/parser/ml_classifier.py` | TF-IDF + LogisticRegression |
| Скоринг | `systems/parser/lead_scoring.py` | 0-100 баллов, тир HOT/WARM/COLD |
| Отклики | `systems/parser/outreach_generator.py` | Генерация персонализированных откликов |
| Алексей | `systems/alexey/main.py` | Pyrogram userbot |
| Гвен | `systems/gwen/commander.py` | Supervisor aiogram bot (63K) |
| Дашборд | `systems/dashboard/main.py` | FastAPI :8000 |
| Парсер | `apps/today_parser.py` | Real-time парсинг чатов |
| RL агент | `systems/alexey/rl_agent.py` | Thompson Sampling адаптация |

---

## Технологический стек

| Категория | Технологии |
|-----------|-----------|
| Язык | Python 3.10+ |
| Telegram | Pyrogram 2.0 (User API), aiogram 3.x (Bot API) |
| AI/LLM | OpenRouter (DeepSeek, Gemini, Claude), Ollama (qwen2.5) |
| ML/NLP | scikit-learn, transformers (BERT), sentence-transformers, PyTorch |
| Web | FastAPI, uvicorn |
| БД | SQLAlchemy async, SQLite (vacancies.db, bot_data.db), PostgreSQL option |
| Кеш/Очередь | Redis, Celery |
| Надёжность | pybreaker (Circuit Breaker), retry механизм |
| Логи | structlog, python-json-logger |
| Контейнеры | Docker, docker-compose |

---

## Запуск

```bash
# Минимальный (Алексей + Дашборд)
./run.sh

# Полный стек
./start_all.sh

# Остановка
./stop_all.sh

# Только дашборд
./run_dashboard.sh
```

### Компоненты полного стека (start_all.sh)

1. `systems/alexey/main.py` — Userbot Алексей
2. `apps/today_parser.py` — Real-time парсер
3. `apps/chat_joiner.py` — Вступление в новые чаты
4. `systems/gwen/bot.py` — Supervisor Bot Гвен
5. `systems/miniapp/api.py` — Telegram Mini App API

---

## Конфигурация (.env)

Все переменные окружения документированы в `.env.example`.
Ключевые:

| Переменная | Описание |
|-----------|---------|
| `TELEGRAM_API_ID/HASH` | User API credentials (my.telegram.org) |
| `OPENROUTER_API_KEY` | Ключ для облачных LLM |
| `SUPERVISOR_BOT_TOKEN` | Токен бота Гвен |
| `SUPERVISOR_CHAT_ID` | Куда Гвен отправляет лиды |
| `AUTO_OUTREACH` | `true` = автоматическая отправка, `false` = ручное |
| `VACANCY_DB_PATH` | Путь к SQLite БД вакансий |
| `MONITORED_CHATS` | ID чатов для мониторинга |
| `CORS_ORIGINS` | Разрешённые origin для дашборда |
