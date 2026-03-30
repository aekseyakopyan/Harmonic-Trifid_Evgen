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
            ['#leads', 'Работа с лидами'],
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

      {/* Leads */}
      <section id="leads" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">👥 Таблица лидов</h2>
        <p className="text-sm text-white/80">Основная рабочая страница. Отображает все лиды с фильтрацией и сортировкой.</p>

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
            <tbody className="space-y-1">
              {[
                ['☐ Чекбокс', 'Выбор лида для массового действия'],
                ['Лид', 'Имя / @username, ссылка на карточку'],
                ['Тир', 'HOT/WARM/COLD — при наведении появляются кнопки смены тира'],
                ['Скор', 'Числовой балл от 0 до 100, полоска-индикатор'],
                ['★ Целевой', 'Ручная оценка 1-5: насколько лид целевой'],
                ['★ Подходит', 'Ручная оценка 1-5: насколько нам подходит'],
                ['Ниша', 'Направление работы лида'],
                ['Статус', 'Стадия воронки'],
                ['Последнее', 'Время последнего взаимодействия'],
              ].map(([col, desc]) => (
                <tr key={col} className="border-b border-border/30">
                  <td className="py-1.5 px-2 font-medium text-white">{col}</td>
                  <td className="py-1.5 px-2">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="font-medium text-sm">Быстрая смена тира (inline)</h3>
        <p className="text-sm text-white/70">
          При наведении на строку лида в колонке «Тир» появляются кнопки 🔥 WARM 🌡 COLD ❄️.
          Нажмите для мгновенного изменения без открытия карточки.
        </p>

        <h3 className="font-medium text-sm">Экспорт в CSV</h3>
        <p className="text-sm text-white/70">
          Кнопка <strong className="text-white">CSV</strong> в правом верхнем углу экспортирует
          текущую выборку (с учётом активных фильтров по тиру и статусу).
        </p>
      </section>

      {/* Bulk actions */}
      <section id="bulk" className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">☑️ Массовые действия</h2>
        <p className="text-sm text-white/80">Позволяют обработать несколько лидов одновременно.</p>

        <h3 className="font-medium text-sm">Как использовать:</h3>
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
            <br />При наличии username — кнопка <strong className="text-accent">TG</strong> открывает
            Telegram-чат напрямую (только в браузере с установленным Telegram).
          </li>
          <li>
            <strong className="text-white">Редактирование</strong> — смена тира (HOT/WARM/COLD),
            статуса, ниши и источника (изменения применяются по потере фокуса).
          </li>
          <li>
            <strong className="text-white">Оригинальные сообщения</strong> — тексты вакансий из базы
            vacancies.db, по которым был создан лид.
          </li>
          <li>
            <strong className="text-white">Оценка лида</strong> — ручная оценка по двум осям:
            <br />• «Целевой» (1-5): насколько лид вообще является нашей ЦА
            <br />• «Подходит» (1-5): насколько подходит под наш профиль работы
            <br />• Заметки: произвольный текст
          </li>
          <li>
            <strong className="text-white">Последний диалог</strong> — последние 5 сообщений
            из активной переписки с кнопкой перехода.
          </li>
          <li>
            <strong className="text-white">История изменений</strong> — лог всех действий:
            патч полей, перезапуск pipeline, архивирование.
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
        <p className="text-sm text-white/80">Управление перепиской Алексея с лидами.</p>

        <ul className="text-sm space-y-2 text-white/70">
          <li>
            <strong className="text-white">Список диалогов</strong> — фильтрация по статусу
            (active / stopped / done), поиск по имени.
          </li>
          <li>
            <strong className="text-white">Детальная страница диалога</strong>:
            <ul className="ml-4 mt-1 space-y-1">
              <li>- Просмотр всей переписки</li>
              <li>- Ручная отправка сообщения от имени Алексея</li>
              <li>- Переключение авто-режима (auto_mode: вкл/выкл)</li>
              <li>- Остановка диалога</li>
            </ul>
          </li>
          <li>
            <strong className="text-white">Иконки:</strong> 🤖 = авто-ответ Алексея, ✏️ = ручное сообщение
          </li>
        </ul>

        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Диалог создаётся нажатием кнопки «Диалог» в карточке лида. Система автоматически
          формирует первое сообщение на основе промпта.
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
            ['Оценка «Целевой»', 'Гистограмма распределения qual_score 1-5'],
            ['Оценка «Подходит»', 'Гистограмма распределения fit_score 1-5'],
            ['Тренд оценок', 'Динамика среднего qual/fit score по дням'],
            ['Воронка вакансий', 'Сколько принято/отклонено на входе'],
            ['Нагрузка Алексея', 'Сообщения по часам суток за 7 дней'],
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
          <div><span className="text-red-400 font-bold">L1</span> — Жёсткие блоки: исполнители, крипто-скамы, MLM, спам-рассылки, дубликаты. Нет шанса быть клиентом.</div>
          <div><span className="text-amber-400 font-bold">L2</span> — Скоринг: суммарный балл ниже порога. Слабые сигналы.</div>
          <div><span className="text-indigo-400 font-bold">ML</span> — Классификатор: модель предсказала «не целевой» (порог 0.60).</div>
          <div><span className="text-purple-400 font-bold">LLM</span> — LLM-верификатор: финальный отсев сомнительных кандидатов.</div>
        </div>

        <p className="text-sm text-white/70">
          Страница показывает топ-20 причин отклонения с процентным вкладом каждой.
          Это помогает выявить паттерны, которые нужно добавить или скорректировать в фильтре.
        </p>

        <div className="bg-surface rounded-lg p-3 text-xs text-muted">
          💡 Если большинство отклонений приходится на «Other» — значит, rejection_reason
          не сохраняется. Проверьте поле в vacancies.db.
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
          Слова и паттерны для L1 жёсткой блокировки. Добавляйте через форму,
          удаляйте кнопкой «✕» рядом со словом.
          Типы: <code className="text-xs bg-surface px-1 rounded">keyword</code>,{' '}
          <code className="text-xs bg-surface px-1 rounded">username</code>,{' '}
          <code className="text-xs bg-surface px-1 rounded">channel</code>.
        </p>

        <h3 className="font-medium text-sm">Промпты</h3>
        <p className="text-sm text-white/70">
          Шаблоны сообщений Алексея. Раздел «Промпты» позволяет:
          редактировать активный промпт, просматривать историю версий,
          откатываться к предыдущей версии.
        </p>
      </section>

      {/* HOT notifications */}
      <section className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">🔔 Уведомления HOT лидов</h2>
        <p className="text-sm text-white/80">
          Когда лид получает тир <strong className="text-red-400">HOT</strong>, в правом нижнем углу
          экрана появляется всплывающее уведомление. Уведомление исчезает через 5 секунд
          или при нажатии на крестик.
        </p>
        <p className="text-sm text-white/70">
          Уведомления работают через WebSocket — получение мгновенное, без необходимости
          обновлять страницу.
        </p>
      </section>

      {/* Mobile */}
      <section className="card space-y-3">
        <h2 className="text-lg font-semibold border-b border-border pb-2">📱 Мобильная версия</h2>
        <p className="text-sm text-white/80">
          Дашборд адаптирован для мобильных устройств:
        </p>
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
