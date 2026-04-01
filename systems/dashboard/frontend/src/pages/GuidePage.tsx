export default function GuidePage() {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Инструкция по работе с дашбордом</h1>
        <p className="text-muted text-sm">Harmonic Trifid Dashboard v2 — руководство пользователя</p>
      </div>

      {/* Navigation */}
      <nav className="card p-3">
        <p className="text-xs text-muted mb-2 uppercase tracking-wide">Содержание</p>
        <div className="grid grid-cols-2 gap-1 text-sm">
          {[
            ['#overview', 'Обзор'],
            ['#workflow', 'Как работает система'],
            ['#vacancies', 'Вакансии'],
            ['#leads', 'Работа с лидами'],
            ['#leadactions', 'Написать / Спам'],
            ['#leadcard', 'Карточка лида'],
            ['#bulk', 'Массовые действия'],
            ['#dialogs', 'Диалоги'],
            ['#analytics', 'Аналитика'],
            ['#filterstats', 'Статистика фильтрации'],
            ['#pipeline', 'Pipeline / Настройки'],
          ].map(([href, label]) => (
            <a key={href} href={href} className="text-accent hover:text-white transition-colors py-0.5">
              → {label}
            </a>
          ))}
        </div>
      </nav>

      {/* Overview */}
      <section id="overview" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">🏠 Обзор (главная)</h2>
        <p className="text-sm text-white/80">
          Главная страница показывает ключевые метрики системы в реальном времени:
        </p>
        <ul className="text-sm space-y-1.5 text-white/70 list-none">
          <li>• <strong className="text-white">Всего лидов</strong> — активные (не архивные) лиды в системе</li>
          <li>• <strong className="text-white">HOT / WARM / COLD</strong> — разбивка по тирам</li>
          <li>• <strong className="text-white">Новых сегодня / за неделю</strong> — поступление лидов</li>
          <li>• <strong className="text-white">Активных диалогов</strong> — текущие переписки</li>
          <li>• <strong className="text-white">Последние лиды</strong> — 5 самых новых записей</li>
        </ul>
        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Страница обновляется автоматически через WebSocket при появлении новых лидов.
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">⚡ Как работает система</h2>
        <p className="text-sm text-white/80">Полный цикл от вакансии до лида:</p>

        <div className="space-y-2">
          {[
            ['1. Парсер', 'Парсит сообщения из Telegram-чатов (вакансии, запросы на услуги). Результаты сохраняются в vacancies.db.'],
            ['2. Фильтр (7 уровней)', 'Каждое сообщение проходит многоуровневую проверку: жёсткие блоки L1 → эвристический скоринг L2 → BERT-классификатор → LLM-верификатор. Принятые получают статус accepted.'],
            ['3. Вакансии', 'Все принятые и отклонённые записи видны в разделе «Вакансии». Это полный лог работы парсера.'],
            ['4. Лиды', 'Принятые вакансии с контактом (t.me/username) конвертируются в лиды. Лид = потенциальный клиент, которому можно написать.'],
            ['5. Отклик', 'Для каждого лида система генерирует черновик сообщения (draft_response) с учётом ниши и кейсов агентства.'],
            ['6. Ксения (userbot)', 'Рассылает отклики от имени специалиста. Ведёт диалоги, адаптирует стиль, отслеживает результат.'],
          ].map(([step, desc]) => (
            <div key={step} className="flex gap-3 text-sm">
              <span className="text-accent font-medium whitespace-nowrap shrink-0 w-36">{step}</span>
              <span className="text-white/70">{desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Vacancies */}
      <section id="vacancies" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">💼 Вакансии</h2>
        <p className="text-sm text-white/80">
          Полный лог всех сообщений, обработанных парсером — принятых и отклонённых.
        </p>

        <h3 className="font-medium text-sm">Статусы</h3>
        <div className="space-y-1.5 text-sm text-white/70">
          <div className="flex gap-2">
            <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400 shrink-0">Принят</span>
            <span>Прошёл все уровни фильтра, есть контакт для отклика</span>
          </div>
          <div className="flex gap-2">
            <span className="px-2 py-0.5 rounded-full text-xs bg-red-500/20 text-red-400 shrink-0">Отклонён</span>
            <span>Не прошёл фильтр. Причина отклонения указана в карточке.</span>
          </div>
          <div className="flex gap-2">
            <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-500/20 text-yellow-400 shrink-0">Пропущен</span>
            <span>Нет черновика ответа (направление вне нашей специализации)</span>
          </div>
          <div className="flex gap-2">
            <span className="px-2 py-0.5 rounded-full text-xs bg-gray-500/20 text-gray-400 shrink-0">Блок-лист</span>
            <span>Источник или контакт в чёрном списке</span>
          </div>
          <div className="flex gap-2">
            <span className="px-2 py-0.5 rounded-full text-xs bg-blue-500/20 text-blue-400 shrink-0">Отправлен</span>
            <span>Отклик уже был отправлен этому контакту</span>
          </div>
          <div className="flex gap-2">
            <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/20 text-purple-400 shrink-0">Диалог</span>
            <span>С этим контактом уже ведётся активный диалог</span>
          </div>
        </div>

        <h3 className="font-medium text-sm">Фильтрация и поиск</h3>
        <p className="text-sm text-white/70">
          Кнопки статусов вверху страницы — кликабельные фильтры. Поиск работает по тексту, источнику и контакту.
          Пагинация по 100 записей.
        </p>

        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Если много нецелевых попадает в «Принятые» — нажмите на них кнопку «Спам» в разделе Лиды,
          они уйдут в чёрный список автоматически.
        </div>
      </section>

      {/* Leads */}
      <section id="leads" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">👥 Таблица лидов</h2>
        <p className="text-sm text-white/80">
          Лиды — это принятые вакансии с контактом (t.me/username), конвертированные для работы.
          Здесь основной рабочий список для ручного или автоматического отклика.
        </p>

        <h3 className="font-medium text-sm">Фильтры</h3>
        <ul className="text-sm space-y-1.5 text-white/70">
          <li>• <strong className="text-white">Поиск</strong> — по имени или @username</li>
          <li>• <strong className="text-white">Тир</strong> — HOT / WARM / COLD</li>
          <li>• <strong className="text-white">Статус</strong> — new / contacted / qualified / lost</li>
          <li>• <strong className="text-white">Оценка</strong> — фильтр по qual_score (★★★★★ до ★☆☆☆☆)</li>
          <li>• <strong className="text-white">Активные / Архив</strong> — переключение режима</li>
        </ul>

        <h3 className="font-medium text-sm">Колонки таблицы</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-white/70 border-collapse">
            <thead>
              <tr className="border-b border-border text-muted">
                <th className="py-1.5 px-2 text-left">Колонка</th>
                <th className="py-1.5 px-2 text-left">Описание</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['☐ Чекбокс', 'Выбор для массового действия'],
                ['Лид', 'Имя, @username и краткий текст запроса из вакансии'],
                ['Тир', 'HOT/WARM/COLD — при наведении появляются кнопки смены тира'],
                ['Скор', 'Числовой балл 0–100, полоска-индикатор'],
                ['★ Целевой', 'Ручная оценка 1–5: насколько лид целевой для нас'],
                ['★ Подходит', 'Ручная оценка 1–5: насколько нам подходит задача'],
                ['Ниша', 'Направление: SEO, контекст, Авито, сайты и т.д.'],
                ['Статус', 'Стадия воронки'],
                ['Последнее', 'Время последнего взаимодействия'],
                ['Действия', '✉ Написать · 🚫 Спам · → Карточка (появляются при наведении)'],
              ].map(([col, desc]) => (
                <tr key={col} className="border-b border-border/30">
                  <td className="py-1.5 px-2 font-medium text-white">{col}</td>
                  <td className="py-1.5 px-2">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Lead actions */}
      <section id="leadactions" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">✉️ Написать лиду / 🚫 Спам</h2>
        <p className="text-sm text-white/80">
          При наведении на строку лида в правом углу появляются две быстрые кнопки действий.
        </p>

        <div className="space-y-4">
          <div className="bg-surface rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-green-400 font-medium text-sm">✉ Написать лиду</span>
            </div>
            <ul className="text-sm text-white/70 space-y-1">
              <li>1. Открывает модалку с готовым черновиком отклика</li>
              <li>2. Черновик сгенерирован на основе ниши лида и кейсов агентства</li>
              <li>3. Кнопка <strong className="text-white">Скопировать</strong> — копирует текст в буфер</li>
              <li>4. Кнопка <strong className="text-accent">Открыть в Telegram</strong> — открывает чат t.me/username</li>
              <li>5. Статус лида автоматически переходит в <code className="text-xs bg-card px-1 rounded">contacted</code></li>
            </ul>
          </div>

          <div className="bg-surface rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-red-400 font-medium text-sm">🚫 Это спам</span>
            </div>
            <ul className="text-sm text-white/70 space-y-1">
              <li>1. Мгновенно архивирует лид со статусом <code className="text-xs bg-card px-1 rounded">spam</code></li>
              <li>2. Username добавляется в pipeline_blacklist — парсер больше не будет его обрабатывать</li>
              <li>3. Система автоматически определяет причину: «Авто-бот биржи вакансий», «Ищут дизайнера», «Бот биржи труда» и т.д.</li>
              <li>4. Причина отображается в уведомлении внизу экрана</li>
            </ul>
          </div>
        </div>

        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Черновик берётся из vacancies.db (поле draft_response). Если черновика нет — отображается текст «Черновик не найден — напиши вручную».
        </div>
      </section>

      {/* Bulk actions */}
      <section id="bulk" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">☑️ Массовые действия</h2>
        <p className="text-sm text-white/80">Позволяют обработать несколько лидов одновременно.</p>

        <ol className="text-sm space-y-1.5 text-white/70 list-decimal list-inside">
          <li>Отметьте нужные лиды галочками (чекбокс в первой колонке)</li>
          <li>Появится панель «Выбрано: N»</li>
          <li>Выберите действие:</li>
        </ol>
        <div className="ml-4 space-y-1 text-sm text-white/70">
          <div>• <span className="text-red-400">🔥 HOT</span> — установить тир HOT</div>
          <div>• <span className="text-amber-400">🌡 WARM</span> — установить тир WARM</div>
          <div>• <span className="text-green-400">✓ Квал</span> — статус «qualified»</div>
          <div>• <span className="text-muted">Архив</span> — переместить в архив</div>
        </div>
        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Чтобы выбрать всю страницу — нажмите чекбокс в шапке таблицы. Крестик в баре снимает выделение.
        </div>
      </section>

      {/* Lead card */}
      <section id="leadcard" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">📋 Карточка лида</h2>
        <p className="text-sm text-white/80">Детальная страница одного лида.</p>

        <h3 className="font-medium text-sm">Блоки карточки:</h3>
        <ul className="text-sm space-y-2 text-white/70">
          <li>
            <strong className="text-white">Основное</strong> — Telegram ID, скор, стадия pipeline,
            приоритет, время последнего действия.
            При наличии username — кнопка <strong className="text-accent">TG</strong> открывает Telegram-чат напрямую.
          </li>
          <li>
            <strong className="text-white">Редактирование</strong> — смена тира (HOT/WARM/COLD),
            статуса, ниши и источника (применяются по потере фокуса).
          </li>
          <li>
            <strong className="text-white">Оригинальные сообщения</strong> — тексты вакансий из
            vacancies.db, по которым был создан лид.
          </li>
          <li>
            <strong className="text-white">Оценка лида</strong> — ручная оценка по двум осям:
            «Целевой» (1–5) и «Подходит» (1–5), плюс текстовые заметки.
          </li>
          <li>
            <strong className="text-white">Последний диалог</strong> — последние 5 сообщений
            из переписки с кнопкой перехода.
          </li>
          <li>
            <strong className="text-white">История изменений</strong> — лог всех действий:
            патч полей, перезапуск pipeline, архивирование, mark_spam.
          </li>
        </ul>

        <h3 className="font-medium text-sm">Кнопки действий:</h3>
        <ul className="text-sm space-y-1 text-white/70">
          <li>• <strong className="text-white">Диалог</strong> — начать новую переписку</li>
          <li>• <strong className="text-white">Перезапуск</strong> — сбросить pipeline_stage, пересчитать</li>
          <li>• <strong className="text-red-400">Архив</strong> — убрать лид из активных (с подтверждением)</li>
        </ul>
      </section>

      {/* Dialogs */}
      <section id="dialogs" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">💬 Диалоги</h2>
        <p className="text-sm text-white/80">Управление перепиской Ксении с лидами.</p>

        <ul className="text-sm space-y-2 text-white/70">
          <li>
            <strong className="text-white">Список диалогов</strong> — фильтрация по статусу
            (active / stopped / done), поиск по имени.
          </li>
          <li>
            <strong className="text-white">Детальная страница диалога</strong>:
            <ul className="ml-4 mt-1 space-y-1">
              <li>- Просмотр всей переписки</li>
              <li>- Ручная отправка сообщения от имени Ксении</li>
              <li>- Переключение авто-режима (auto_mode: вкл/выкл)</li>
              <li>- Остановка диалога</li>
            </ul>
          </li>
          <li>
            <strong className="text-white">Иконки:</strong> 🤖 = авто-ответ Ксении, ✏️ = ручное сообщение
          </li>
        </ul>

        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Диалог создаётся нажатием кнопки «Диалог» в карточке лида. Система формирует
          первое сообщение на основе промпта и истории чата.
        </div>
      </section>

      {/* Analytics */}
      <section id="analytics" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">📊 Аналитика</h2>
        <p className="text-sm text-white/80">Графики и метрики работы системы.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          {[
            ['Поток лидов', 'Новые лиды по дням/часам за выбранный период'],
            ['По нишам', 'Топ-10 ниш по количеству лидов'],
            ['По источникам', 'Распределение лидов по Telegram-каналам'],
            ['Оценка «Целевой»', 'Гистограмма распределения qual_score 1–5'],
            ['Оценка «Подходит»', 'Гистограмма распределения fit_score 1–5'],
            ['Тренд оценок', 'Динамика среднего qual/fit score по дням'],
            ['Воронка вакансий', 'Сколько принято/отклонено на входе'],
            ['Нагрузка Ксении', 'Сообщения по часам суток за 7 дней'],
          ].map(([name, desc]) => (
            <div key={name} className="bg-surface rounded-lg p-3">
              <p className="font-medium text-white text-xs mb-0.5">{name}</p>
              <p className="text-xs text-muted">{desc}</p>
            </div>
          ))}
        </div>

        <p className="text-sm text-white/70">
          Переключение периода: <strong className="text-white">День / Неделя / Месяц</strong> в правом верхнем углу.
        </p>
      </section>

      {/* Filter stats */}
      <section id="filterstats" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">🔍 Статистика фильтрации</h2>
        <p className="text-sm text-white/80">
          Анализ работы многоуровневого фильтра вакансий. Доступен в боковом меню «Фильтр».
        </p>

        <h3 className="font-medium text-sm">Уровни фильтрации:</h3>
        <div className="space-y-2 text-sm text-white/70">
          <div><span className="text-red-400 font-bold">L1</span> — Жёсткие блоки: исполнители, дизайнеры, найм сотрудников, крипто-скамы, MLM, дубликаты.</div>
          <div><span className="text-amber-400 font-bold">L2</span> — Эвристический скоринг: суммарный балл ниже порога. Штрафы за нерелевантную нишу, бонусы за запросы по нашим направлениям.</div>
          <div><span className="text-indigo-400 font-bold">ML</span> — BERT-классификатор: модель предсказала «не целевой» (порог 0.60).</div>
          <div><span className="text-purple-400 font-bold">LLM</span> — LLM-верификатор: финальный отсев сомнительных кандидатов.</div>
        </div>

        <h3 className="font-medium text-sm">Наши целевые ниши:</h3>
        <div className="flex flex-wrap gap-1.5 text-xs">
          {['SEO', 'Контекстная реклама', 'Авито', 'Разработка сайтов', 'SMM', 'Маркетинг'].map(n => (
            <span key={n} className="px-2 py-0.5 bg-green-500/10 text-green-400 rounded">{n}</span>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5 text-xs">
          <span className="text-muted text-xs">Отклоняются:</span>
          {['Дизайнеры', 'Видеографы', 'Копирайтеры', 'Найм сотрудников', 'Маркетплейсы', 'Веб-дизайн'].map(n => (
            <span key={n} className="px-2 py-0.5 bg-red-500/10 text-red-400 rounded">{n}</span>
          ))}
        </div>

        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Если нецелевые всё равно проходят — использuj кнопку «Спам» в таблице лидов.
          Username автоматически добавится в blacklist.
        </div>
      </section>

      {/* Pipeline */}
      <section id="pipeline" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">⚙️ Pipeline / Настройки</h2>

        <h3 className="font-medium text-sm">Конфигурация</h3>
        <p className="text-sm text-white/70">
          Ключевые параметры системы (пороги скоров, задержки, лимиты).
          Редактируются inline — нажмите значение, измените, нажмите Enter.
        </p>

        <h3 className="font-medium text-sm">Чёрный список</h3>
        <p className="text-sm text-white/70">
          Слова, паттерны и username для L1 жёсткой блокировки. Пополняется автоматически
          при нажатии «Спам» на лиде. Добавляйте вручную через форму,
          удаляйте кнопкой «✕».
          Типы: <code className="text-xs bg-surface px-1 rounded">word</code>,{' '}
          <code className="text-xs bg-surface px-1 rounded">channel</code>,{' '}
          <code className="text-xs bg-surface px-1 rounded">niche</code>.
        </p>

        <h3 className="font-medium text-sm">Промпты</h3>
        <p className="text-sm text-white/70">
          Шаблоны сообщений Ксении. Раздел «Промпты» позволяет:
          редактировать активный промпт, просматривать историю версий,
          откатываться к предыдущей версии.
        </p>
      </section>

      {/* HOT notifications */}
      <section className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">🔔 Уведомления HOT лидов</h2>
        <p className="text-sm text-white/80">
          Когда лид получает тир <strong className="text-red-400">HOT</strong> — в правом нижнем углу
          появляется всплывающее уведомление. Исчезает через 5 секунд или при нажатии крестика.
          Работает через WebSocket — мгновенно, без перезагрузки страницы.
        </p>
      </section>

      {/* Mobile */}
      <section className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">📱 Мобильная версия</h2>
        <ul className="text-sm space-y-1 text-white/70">
          <li>• На экранах &lt;768px боковое меню скрыто</li>
          <li>• Открывается кнопкой ☰ в верхней панели</li>
          <li>• Закрывается нажатием на фон или крестик</li>
          <li>• Таблицы прокручиваются горизонтально</li>
        </ul>
      </section>

      <div className="text-xs text-muted text-center pt-4 pb-8">
        Harmonic Trifid Dashboard v2 · {new Date().getFullYear()}
      </div>
    </div>
  )
}
