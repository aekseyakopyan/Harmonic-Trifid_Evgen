"""
VacancyScorer — фильтр входящих сообщений.

Принимаем ТОЛЬКО: малый/средний бизнес ищет SEO-специалиста или настройку Яндекс.Директ.
Всё остальное — reject.

Архитектура:
  1. Дедупликация
  2. HARD REJECT (спам / штатный найм / самопрезентация / не та ниша / язык / крипто)
  3. Специализация → только SEO или контекстная реклама
  4. Demand-сигнал → должен быть хотя бы один (клиент ищет, не продаёт)
  5. Score → ранжирование качества лида
"""

import re
import hashlib
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, timezone


# ─── ДЕДУПЛИКАТОР ─────────────────────────────────────────────────────────────

class MessageDeduplicator:
    def __init__(self, ttl_hours=48):
        self.seen_hashes: Dict[str, datetime] = {}
        self.ttl = timedelta(hours=ttl_hours)

    def is_duplicate(self, text: str, timestamp: datetime = None) -> bool:
        normalized = re.sub(r'[\U00010000-\U0010ffff]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()[:200]
        h = hashlib.md5(normalized.encode()).hexdigest()
        now = timestamp or datetime.utcnow()
        # Удаляем устаревшие
        expired = [k for k, ts in self.seen_hashes.items() if now - ts > self.ttl]
        for k in expired:
            del self.seen_hashes[k]
        if h in self.seen_hashes:
            return True
        self.seen_hashes[h] = now
        return False


# ─── SCORER ───────────────────────────────────────────────────────────────────

class VacancyScorer:
    """Анализатор релевантности: SEO и Яндекс.Директ запросы от бизнеса."""

    # =========================================================================
    # СПЕЦИАЛИЗАЦИИ — только эти два направления принимаем
    # =========================================================================

    SEO_KEYWORDS = [
        r"\bseo\b", r"\bсео\b", r"\bсеошник\w*\b",
        r"поисков\w+\s+оптимизаци",
        r"продвижени\w+\s+сайт",
        r"вывод\w*\s+в\s+топ",
        r"seo[- ]специалист", r"seo[- ]аудит", r"seo[- ]копирайт",
        r"\bоптимизатор\b",
        r"\bлинкбилдинг\b", r"\blinkbuilding\b",
        r"семантическ\w+\s+ядр",
        r"технический\s+аудит\s+сайт",
        r"органическ\w+\s+трафик",
        r"поисков\w+\s+трафик",
        r"\bкластеризаци\w*\b", r"\bперелинковк\w*\b",
        r"аудит\s+сайт\w*",
        r"вывести\s+сайт\s+в\s+(?:поиск|топ)",
        r"поднять\s+сайт\s+в\s+выдач",
        r"нужно?\s+сео", r"нужно?\s+seo",
        r"продвиньте\s+сайт",
        r"поведенческ\w+\s+фактор",
        r"внешн\w+\s+(?:оптимизаци|ссылк)",
        r"(?:google|гугл)\s+(?:search\s+console|вебмастер)",
        r"яндекс\s+вебмастер",
        r"(?:наращивание|закупка)\s+(?:ссылок|ссылочн)",
        r"(?:title|description|мета[- ]?теги)",
        r"нужен\s+(?:seo|seo-|сео)[- ]?\w*",
        r"(?:продвижение|раскрутка)\s+(?:в\s+)?(?:google|яндекс|поиск)",
    ]

    PPC_KEYWORDS = [
        r"контекстн\w+\s+реклам",
        r"яндекс\.?директ", r"\bдирект\b",
        r"google\s+ads", r"google\s+adwords",
        r"\bppc\b",
        r"\bконтекстолог\w*\b", r"\bдиректолог\w*\b",
        r"поисков\w+\s+реклам",
        r"\bрся\b", r"\bкмс\b",
        r"настройк\w+\s+контекст",
        r"ведени\w+\s+реклам\w*\s+директ",
        r"оптимизаци\w+\s+ставок",
        r"реклама\s+в\s+поиске",
        r"контекст\s+под\s+ключ",
        r"запустить\s+директ", r"настроить\s+яндекс",
        r"нужна\s+реклама\s+в\s+яндексе",
        r"хочу\s+лидов\s+из\s+поиска",
        r"настройте\s+рекламу",
        r"(?:ведение|настройка|оптимизация)\s+(?:рекламн\w+\s+)?кампани\w+",
        r"(?:реклама|продвижение)\s+в\s+яндекс",
        r"(?:минус[- ]?слова|минусовка)",
        r"(?:конверси\w+|cpa|cpc|ctr)\s+(?:оптимизаци|улучш)",
        r"товарная\s+кампания",
    ]

    # =========================================================================
    # HARD REJECT — одно совпадение = немедленный reject
    # =========================================================================

    # 1. Штатный найм: ищут сотрудника в штат, а не подрядчика
    HIRING_PATTERNS = [
        # Зарплата / оклад
        r"(?:зарплата|зп|з/п|оклад|ставка)\s*[:\-]?\s*(?:от|до|:)?\s*\d",
        r"(?:зп|з/п)\s+\d",
        r"доход\s+(?:от|до)\s+\d+\s*(?:тыс|₽|руб|к\b)",
        r"(?:первый|испытательный)\s+месяц.{0,30}\d",
        r"\bиспытательный\s+срок\b",
        r"(?:full[- ]?time|part[- ]?time|фулл[- ]?тайм|парт[- ]?тайм)",
        r"(?:принимаем|рассматриваем|ждём)\s+резюме",
        r"(?:пришли|прислали|отправьте?|направьте?)\s+(?:своё\s+)?резюме",
        r"резюме\s+(?:на|по|в)\s+\w+",
        r"hh\.ru/\w+",  # HeadHunter ссылки
        r"superjob\.ru",
        # "Вакансия: [роль]"
        r"(?:💡|📌|🔥|⭐)?\s*вакансия\s*[:\-!]\s*",
        r"(?:открыта|открываем)\s+вакансия",
        # Набор в команду/штат
        r"набираем\s+(?:команду|сотрудников|специалистов|менеджеров)",
        r"в\s+(?:нашу?\s+)?команд[ую]\s+(?:нужен|ищем|требуется|требуются)",
        r"ищем\s+(?:сотрудника|специалиста|менеджера|маркетолога|директолога|контекстолога|таргетолога).{0,40}(?:в\s+(?:штат|команду|офис)|зарплат|оклад|ставк)",
        r"рассматриваем\s+кандидатов",
        r"\bштатн\w+\s+(?:должность|специалист|сотрудник)\b",
        r"работа\s+(?:на\s+постоянной?\s+основе|в\s+офисе|в\s+штат)",
        r"(?:удалённая|удаленная)\s+работа.{0,40}(?:зарплат|зп|оклад|\d+\s*(?:₽|руб|тыс))",
        # Маркетплейс-менеджмент (не SEO/PPC)
        r"ведение\s+магазин\w*.{0,30}(?:ozon|озон|wb|wildberries|маркетплейс)",
        r"(?:ozon|озон|wb|wildberries).{0,30}(?:нужен|ищем|ведение|управление|менеджер)",
        r"\b(?:wb|вб|wildberries|ozon|озон)\s+(?:продавец|магазин|менеджер|аналитик|специалист)",
        r"\bабс[- ]?анализ\b",  # ABC-анализ = маркетплейс
        r"abc[- ]?анализ\b",
        r"продвижение\s+на\s+(?:ozon|озон|wb|wildberries|маркетплейс)",
        r"seo\s+(?:для|на)\s+(?:ozon|озон|wb|wildberries|маркетплейс)",  # marketplace SEO ≠ web SEO
        r"карточк\w+\s+(?:товар\w+)?\s*(?:wb|вб|ozon|озон|wildberries)",
        r"инфографик\w+.{0,30}(?:wb|wildberries|ozon|маркетплейс)",
    ]

    # 2. Самопрезентации — человек ПРОДАЁТ услуги, не ПОКУПАЕТ
    OFFER_PATTERNS = [
        # Прямые предложения
        r"(?:предлагаю|выполню|сделаю|настрою|разработаю|создам|запущу|соберу|продвину)\s+(?:как\s+)?(?:для\s+вас\s+|вам\s+)?(?:рекламу|директ|контекст|seo|сео|сайт|лендинг|продвижение)\b",
        r"предлагаю(?: свои)? услуги",
        r"принимаю\s+заказы",
        r"оказываю\s+услуги",
        r"беру\s+(?:в\s+работу|на\s+(?:проект|аутсорс)|заказ)",
        r"возьму\s+в\s+работу",
        r"готов(?:а)?\s+(?:взять|выполнить|приступить|начать|работать)",
        r"открыт(?:а)?\s+(?:для|к)\s+(?:новых?\s+)?(?:сотрудничеств|проект|заказ)",
        r"в\s+поиске\s+(?:новых?\s+)?(?:клиентов|заказов|проектов)",
        r"расширяю\s+(?:портфолио|клиентскую\s+базу)",
        r"набираю\s+(?:клиентов|кейсы|портфолио)",
        # Самопрезентация
        r"меня\s+зовут\s*[–—-]?\s*[А-Я][а-яё]+",
        r"(?:привет|здравствуйте|добрый\s+\w+).{0,30}(?:предлагаю|меня\s+зовут|я\s+(?:веб|маркетолог|директолог|контекстолог|фрилансер|специалист|seo))",
        r"я\s+сертифицированн(?:ый|ая)",
        r"я\s+[А-Я][а-яё]+\s*[–—-]\s*(?:директолог|контекстолог|таргетолог|сеошник|маркетолог|авитолог)",
        r"(?:мой|моя|мои|моё)\s+(?:портфолио|кейс\w*|работ\w+)",
        r"(?:портфолио|кейсы)[:\s]+(?:https?://|t\.me/)",
        r"опыт\s+работы\s*:",
        # Гарантии и скидки (продавец)
        r"(?:гарантирую|гарантия)\s+(?:результат|возврат|качеств)",
        r"(?:бесплатн\w+)\s+(?:аудит|консультаци|разбор)",
        r"(?:со\s+скидкой|акция|спецпредложение)",
        # Хэштеги фрилансера
        r"#(?:фрилансер|исполнитель|разработчик|дизайнер|директолог|контекстолог|таргетолог|seo[- ]специалист|авитолог)\b",
        r"#(?:услуги|кейс|портфолио|ищуработу|ищузаказы)\b",
        # Рекомендует чужие контакты (не покупатель)
        r"скину\s+(?:вам|тебе|им|его|её|их)?\s*(?:контакт|менеджера|специалиста|номер)",
        r"если\s+нужны\s+контакты",
        r"вел(?:а)?\s+(?:директ|контекст|продвижение|рекламу).{0,50}(?:через|в|с)\s+агентств",
        # Другие сигналы продавца
        r"кому\s+нужны\s+клиенты",
        r"могу\s+помочь\s+с\s+(?:seo|директ|рекламой|продвижением)",
        r"помогу\s+с\s+(?:seo|директ|рекламой|продвижением|таргетом)",
        r"оплата\s+(?:до\s+и\s+после|после\s+результата|после\s+получения)",
        r"(?:последнее\s+время\s+)?часто\s+вижу\s+запрос",
    ]

    # 3. Не та ниша / не тот контекст
    WRONG_NICHE_PATTERNS = [
        # SMM / контент
        r"\bsmm\b", r"\bсмм\b", r"smm[- ](?:специалист|менеджер|агентство)",
        r"ведение\s+(?:соцсетей|инстаграм|вконтакте|телеграм[- ]?канал)",
        r"контент[- ](?:план|менеджер|мейкер|стратегия)",
        r"social\s+media\s+(?:marketing|manager)",
        # Таргет (кроме ВК — мы не делаем)
        r"\bтаргетолог\b", r"таргетирован\w+\s+реклам",
        r"facebook\s+ads", r"meta\s+ads", r"instagram\s+ads",
        r"реклам\w+\s+(?:в\s+)?(?:инстаграм|фейсбук|facebook|instagram)",
        r"tg\s+ads", r"telegram\s+ads",
        r"mytarget", r"майтаргет",
        r"vk\s+ads\b",  # только если без SEO/PPC контекста
        # Авито (мы делаем авито, но не принимаем без явного "реклама на авито")
        # → убираем авито из hard reject, пусть scorer обработает
        # Видео / монтаж
        r"\bрилс(?:мейкер)?\b", r"\breels\b", r"\bshorts\b", r"\bтикток\b", r"\btiktok\b",
        r"видео[- ](?:монтаж|контент|мейкер|продакшн)",
        r"монтажёр\b", r"видеограф\b",
        r"(?:ищу|нужен|требуется)\s+(?:рилсмейкер|reels[- ]?maker|reels[- ]?creator)",
        # Дизайн
        r"веб[- ]дизайнер", r"web[- ]дизайнер",
        r"ui[/\-]ux\s+дизайн", r"графическ\w+\s+дизайнер",
        r"моушн[- ]дизайнер", r"motion\s+design",
        # Копирайтинг (не SEO-копирайтинг)
        r"(?<!seo[- ])(?<!seo\s)копирайтер\b", r"копирайтинг\b(?!.{0,10}seo)",
        r"продающ\w+\s+текст", r"написание\s+текстов",
        # Разработка сайтов (не наше направление)
        r"\bфлаттер\b", r"\bflutter\b", r"\bреакт\b(?!\s+нативе)",
        r"разработ\w+\s+(?:приложени|мобильн)",
        r"1с[- ]программист", r"1с[- ]разработ",
        # Email/CRM
        r"email[- ]маркетинг", r"email[- ]рассылк",
        r"\bcrm[- ]маркетолог\b",
        # HR / подбор персонала
        r"\bрекрутер\b", r"hr[- ]менеджер", r"подбор\s+персонала",
        r"холодные\s+звонки", r"call[- ]?центр",
        # Менеджеры продаж (не маркетолог)
        r"менеджер\s+по\s+продажам", r"\bсейлз\b", r"sales\s+manager",
        # Бухгалтерия / юриспруденция
        r"\bбухгалтер\b", r"\bбухгалтери\w+\b", r"\bюрист\b",
        # Инфографика маркетплейсов
        r"\bкарточки?\b.{0,20}(?:wb|wildberries|ozon|озон|вб).{0,20}(?:оптимиз|дизайн|создам|нужн)",
    ]

    # 4. Спам / MLM / крипто / промо
    SPAM_PATTERNS = [
        # Боты и авторепляи бирж вакансий
        r"вакансия здесь размещена",
        r"вакансии здесь размещены",
        r"vakansii", r"vakansii_rabota",
        r"неизвестная\s+команда",
        r"доступные\s+команды\s*:",
        r"this code can be used to log in",
        r"login code:",
        r"freelance_rabota",
        r"если\s+вам\s+нужен\s+фриланс\s+чат",
        # Украинский язык
        r"[єґіїІЇ]", r"\bщо\b", r"\bякщо\b",
        r"\bта\s+(?:й|її|він|вона)\b",
        # Крипто / USDT / скам
        r"\busdt\b", r"\bбинанс\b", r"\bbinanc\w+\b",
        r"\bкрипт\w+\b.{0,30}(?:заработ|доход|инвест)",
        r"покупаю\s+usdt.{0,30}(?:дороже|выше|процент)",
        r"(?:5|10|15|20|25)\s*%\s*(?:выше|дороже)\s*(?:рынка|курса|биржи)",
        r"\bantgroup\b|antgroup_pay|dd18898",
        # MLM / пассивный доход
        r"сетевой\s+(?:маркетинг|бизнес)",
        r"\bмлм\b|\bmлm\b",
        r"пассивный\s+доход.{0,50}(?:от\s+\d+|без\s+вложений)",
        r"без\s+вложений.{0,50}(?:заработ|доход)",
        r"как\s+зарабатывать\s+\d+",
        r"легк\w+\s+деньги", r"лёгк\w+\s+деньги",
        # Курсы / эфиры / обучение
        r"(?:прикладной|полезный|бесплатн\w+)\s+эфир",
        r"(?:записаться|зайти)\s+на\s+эфир",
        r"прогрев\w*\s+к\s+курс",
        r"вебинар\b", r"мастермайнд\b",
        r"пройди\s+бесплатное\s+обучение",
        r"научим\s+зарабатывать",
        # Рассылки / инвайтинг
        r"массов\w+\s+рассылк\w+",
        r"(?:рассылк\w+|инвайтинг|парсинг).{0,30}(?:telegram|тг|tg)\b",
        r"(?:софт|бот)\s+для\s+(?:рассылк|парсинг|инвайтинг)",
        r"рассылка\s+по\s+(?:чатам|группам|базам?)",
        r"твоё\s+сообщение\s+увидят\s+тысячи",
        r"@getclient_tg_bot",
        # Промо-посты
        r"подпишись\s+на\s+канал", r"вступай\s+в\s+группу",
        r"дарю\s+чек[- ]?лист", r"скачать\s+гайд", r"забирай\s+подарок",
        r"реферальная\s+ссылка",
        r"переходи\s+по\s+ссылке",
        r"выплаты\s+ежедневно",
        r"тапать\b", r"хомяк\b",
        r"розыгрыш\s+(?:призов|подарков|айфона|денег)",
        r"участвуй\s+в\s+розыгрыш",
        # Отзывы / накрутка
        r"написани\w+\s+отзывов",
        r"отзывы\s+за\s+деньги",
        r"купить\s+отзывы",
        r"нужны\s+авторы\s+отзывов",
        # Агентства нанимают (не клиент)
        r"(?:smm|digital|маркетингов\w+)\s+агентств\w+\s+(?:ищ|нанима|набира)",
        r"event[- ]агентств",
        r"маркетингово\w+\s+агентств",
        # Предложение работы "черкните" / "#помогу"
        r"черкн(?:ите|и)\s+(?:мне|нам)?\s*в\s+(?:директ|лс|личку|дм)",
        r"напишите?\s+(?:мне|нам)?\s*в\s+(?:директ|директе)\b",
        r"#помогу\b",
        # Посевы / шортс / клонирование
        r"занимаюсь\s+посевами", r"сделаю\s+посевы",
        r"клониров\w+\s+голос\w*",
        # Промышленное / нерелевантное
        r"\bАСУТП\b", r"промышленн\w+\s+автоматизаци",
        # Украина / война (нежелательный контекст)
        r"всу\b.{0,30}(?:пропал|потер|без\s+вести)",
    ]

    # 5. Исключённые локации (СНГ без России)
    EXCLUDED_LOCATIONS = [
        r"\bалмат\w+\b", r"\bказахстан\w*\b", r"\bастана\b",
        r"\bузбекистан\w*\b", r"\bташкент\b",
        r"\bгрузи\w+\b", r"\bтбилис\w+\b",
        r"\bереван\b", r"\bармени\w+\b",
        r"\bбишкек\b", r"\bкыргызстан\w*\b",
    ]

    # =========================================================================
    # DEMAND SIGNALS — клиент ищет подрядчика (не продаёт)
    # =========================================================================

    DEMAND_SIGNALS = [
        # Прямые запросы
        r"\bищу\s+(?:специалиста|подрядчика|фрилансера|контрактора|исполнителя|директолога|контекстолога|seo)\b",
        r"\bищем\s+(?:специалиста|подрядчика|фрилансера|исполнителя|директолога|контекстолога|seo)\b",
        r"\bнужен\s+(?:специалист|подрядчик|фрилансер|директолог|контекстолог|seo[- ]?\w*|маркетолог)\b",
        r"\bнужна\s+(?:реклама|настройка|помощь\s+с|консультация\s+по)\b",
        r"\bнужны?\s+(?:лиды|клиенты|заявки)\s+(?:с|из|через|в)\b",
        r"\bтребуется\s+(?:специалист|подрядчик|фрилансер|помощь)\b",
        r"\bищу\s+(?:кого[\s-]?нибудь|кого|кто)\s+(?:может|умеет|настроит|сделает|занимается)\b",
        # Вопросы и советы
        r"посоветуйте", r"рекомендуйте", r"подскажите",
        r"знает\s+(?:ли\s+)?кто",
        r"кто\s+(?:делал|может|умеет|занимается|берется|возьмется|возьмётся)",
        r"есть\s+(?:кто|контакты|рекомендации)",
        r"дайте\s+контакт", r"нужна\s+консультация",
        # Запрос на выполнение работы
        r"ищу\s+подрядчика",
        r"ищу\s+фрилансера",
        r"требуется\s+исполнитель",
        r"кто\s+возьмется", r"кто\s+готов\s+взяться",
        r"закрыть\s+задачу", r"помогите\s+закрыть",
        r"ищу\s+(?:того\s+)?кто",
        r"нужен\s+человек\s+(?:который|кто)",
        r"кто\s+может\s+реализовать",
        # Биржи и платформы (однозначно клиент)
        r"связаться\s+с\s+заказчиком",
        r"freelancehunt\.com/project",
        r"freelance\.ua/orders",
        r"kwork\.ru/projects",
        r"finder\.work/vacancies",
        r"заказ\s*#\d+",
        r"заполнить\s+(?:анкет|форму)",
        r"откликнуться\s+(?:через|на|по)\s+(?:форму|анкет|ссылк)",
        # Нужно [услуга] — все формы слова
        r"\bнужн[оаы]?\s+(?:продвижени|оптимизаци|настройк|реклам|раскрутк|аудит\s+сайт)",
        r"\bнужн[оаы]?\s+(?:seo|seo[- ]|сео)\b",
        r"\bнужн[оаы]?\s+\w+\s+(?:сайт|в\s+(?:топ|поиск|выдач))",
        # Бизнес-проблема
        r"нет\s+(?:трафика|клиентов|заявок|лидов)\s+(?:с\s+)?(?:сайта|сео|директ|рекламы)",
        r"сайт\s+не\s+(?:в\s+топе|находят|виден|продвигается)",
        r"хочу\s+лидов",
        r"хочу\s+(?:запустить|настроить)\s+рекламу",
        r"хочу\s+вывести\s+сайт",
    ]

    # Сигналы формата заказа — дополнительно к DEMAND
    ORDER_FORMAT_SIGNALS = [
        r"📌\s+\w",           # Kwork маркер
        r"🔥\s*(?:заказ|срочн)",
        r"🙋[‍♂️♀️]*\s",      # заказчик
        r"бюджет\s*:",
        r"дедлайн\s*:",
        r"тз\s*:", r"техзадание\s*:",
    ]

    # =========================================================================
    # МЯГКИЕ ИСКЛЮЧЕНИЯ (штраф -3, не блокируют)
    # =========================================================================

    SOFT_EXCLUSIONS = [
        r"\bjunior\b", r"\bджуниор\b", r"начинающ\w+",
        r"\bстажер\b", r"стажировк\w+", r"\bintern\b",
        r"без\s+опыта",
        r"\bзакрыто\b", r"\bнашли\b", r"исполнитель\s+найден",
        r"вакансия\s+закрыта",
    ]

    # =========================================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================================

    def __init__(self):
        from core.config.settings import settings
        import json, os
        self.target_keywords = [k.strip().lower() for k in settings.TARGET_KEYWORDS.split(",") if k.strip()]
        self.deduplicator = MessageDeduplicator(ttl_hours=48)
        # Динамические фильтры (обучаемые Гвен)
        self.dynamic_filters: Dict = {"positive": [], "negative": []}
        dyn_path = os.path.join(os.path.dirname(__file__), "../../../core/config/dynamic_filters.json")
        if os.path.exists(dyn_path):
            try:
                with open(dyn_path, 'r', encoding='utf-8') as f:
                    self.dynamic_filters = json.load(f)
            except Exception as e:
                print(f"[Scorer] Ошибка загрузки dynamic_filters: {e}")

    # =========================================================================
    # ОСНОВНОЙ МЕТОД
    # =========================================================================

    def analyze_message(self, text: str, message_date: datetime = None) -> Dict:
        t = text.lower()

        # 1. Дедупликация
        if self.deduplicator.is_duplicate(text, message_date):
            return self._reject("Дубликат")

        # 2. Избыток эмодзи (явный спам)
        emoji_count = len(re.findall(r"[\U00010000-\U0010ffff]", text))
        if emoji_count > 25:
            return self._reject(f"Избыток эмодзи ({emoji_count})")
        emoji_penalty = -1 if emoji_count > 15 else 0

        # 3. HARD REJECT — спам
        spam_hit = self._match_any(t, self.SPAM_PATTERNS)
        if spam_hit:
            return self._reject(f"Спам: {spam_hit}")

        # 4. HARD REJECT — штатный найм
        hire_hit = self._match_any(t, self.HIRING_PATTERNS)
        if hire_hit:
            return self._reject(f"Штатный найм: {hire_hit}")

        # 5. HARD REJECT — самопрезентация / предложение услуг
        offer_hit = self._match_any(t, self.OFFER_PATTERNS)
        if offer_hit:
            return self._reject(f"Предложение услуг: {offer_hit}")

        # 6. HARD REJECT — не та ниша
        niche_hit = self._match_any(t, self.WRONG_NICHE_PATTERNS)
        if niche_hit:
            return self._reject(f"Не та ниша: {niche_hit}")

        # 7. HARD REJECT — исключённые локации
        loc_hit = self._match_any(t, self.EXCLUDED_LOCATIONS)
        if loc_hit:
            return self._reject(f"Исключённая локация: {loc_hit}")

        # 8. Динамические негативы (обученные Гвен)
        for pattern in self.dynamic_filters.get("negative", []):
            if re.search(pattern, t, re.IGNORECASE):
                return self._reject(f"Динамический негатив: {pattern}")

        # 9. Специализация — только SEO или Яндекс.Директ
        specialization, spec_score, spec_keywords = self._detect_specialization(t)

        # Проверяем target_keywords из настроек (если нет совпадения по специализации)
        if not specialization:
            kw = self._check_target_keywords(t)
            if kw:
                specialization = "SEO"  # относим к SEO по умолчанию
                spec_score = 3
                spec_keywords = [kw]

        # Динамические позитивы
        if not specialization:
            for pattern in self.dynamic_filters.get("positive", []):
                if re.search(pattern, t, re.IGNORECASE):
                    specialization = "SEO"
                    spec_score = 3
                    spec_keywords = [pattern]
                    break

        if not specialization:
            return self._reject("Специализация не определена (не SEO / не Директ)")

        # 10. Demand-сигнал — клиент должен что-то искать
        demand_score = self._detect_demand(t)
        order_score = self._detect_order_format(t)
        demand_ok = max(demand_score, order_score) > 0

        # Без demand-сигнала нужен высокий spec_score (≥7 невозможен — это reject)
        min_score = 3 if demand_ok else 7

        # 11. Мягкие штрафы
        penalty = self._soft_penalty(t)

        # 12. Бонусы
        remote_bonus = 1 if re.search(r"\bудалённо\b|\bудаленно\b|\bremote\b|из любой точк", t, re.IGNORECASE) else 0
        budget_text = self._extract_budget(text)
        budget_bonus = 1 if budget_text else 0
        freshness_bonus = self._freshness_bonus(message_date) if message_date else 0

        total = spec_score + demand_score + order_score + remote_bonus + budget_bonus + freshness_bonus + penalty + emoji_penalty

        return {
            'is_vacancy': total >= min_score,
            'specialization': specialization,
            'detected_keywords': spec_keywords,
            'relevance_score': total,
            'budget': budget_text,
            'score_breakdown': {
                'spec_score': spec_score,
                'demand_score': demand_score,
                'order_format': order_score,
                'remote': remote_bonus,
                'budget': budget_bonus,
                'freshness': freshness_bonus,
                'penalty': penalty,
                'emoji_penalty': emoji_penalty,
                'min_required': min_score,
            },
            'excluded_specialization': False,
            'excluded_platforms': [],
            'needs_clarification': False,
            'is_agency': False,
        }

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================

    def _match_any(self, text: str, patterns: List[str]) -> Optional[str]:
        """Возвращает первый совпавший паттерн или None."""
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return p
        return None

    def _detect_specialization(self, text: str) -> Tuple[Optional[str], int, List[str]]:
        """SEO (+3) или контекстная реклама (+3). Первое совпадение побеждает."""
        seo_hits = [p for p in self.SEO_KEYWORDS if re.search(p, text, re.IGNORECASE)]
        ppc_hits = [p for p in self.PPC_KEYWORDS if re.search(p, text, re.IGNORECASE)]
        if seo_hits and ppc_hits:
            # Оба — возвращаем тот у кого больше совпадений
            if len(seo_hits) >= len(ppc_hits):
                return "SEO", 3, seo_hits
            return "контекстная реклама", 3, ppc_hits
        if seo_hits:
            return "SEO", 3, seo_hits
        if ppc_hits:
            return "контекстная реклама", 3, ppc_hits
        return None, 0, []

    def _check_target_keywords(self, text: str) -> Optional[str]:
        for kw in self.target_keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                return kw
        return None

    def _detect_demand(self, text: str) -> int:
        """Возвращает +2 если найден demand-сигнал от покупателя."""
        for p in self.DEMAND_SIGNALS:
            if re.search(p, text, re.IGNORECASE):
                return 2
        return 0

    def _detect_order_format(self, text: str) -> int:
        """Возвращает +2 если текст в формате заказа с биржи."""
        for p in self.ORDER_FORMAT_SIGNALS:
            if re.search(p, text, re.IGNORECASE):
                return 2
        return 0

    def _soft_penalty(self, text: str) -> int:
        penalty = 0
        for p in self.SOFT_EXCLUSIONS:
            if re.search(p, text, re.IGNORECASE):
                penalty -= 3
        return penalty

    def _extract_budget(self, text: str) -> Optional[str]:
        patterns = [
            r"(?:бюджет|оплата)\s*:?\s*(\d[\d\s.,]+)\s*(?:₽|руб|тыс|к\b|k\b)",
            r"(?:от|до)\s+(\d[\d\s.,]+)\s*(?:₽|руб|тыс|к\b|k\b)(?!\s*(?:в\s+месяц|мес|первый))",
        ]
        hits = []
        for p in patterns:
            for m in re.finditer(p, text, re.IGNORECASE):
                hits.append(m.group(0).strip())
        return ", ".join(hits) if hits else None

    def _freshness_bonus(self, message_date: datetime) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if message_date and message_date.tzinfo:
            message_date = message_date.replace(tzinfo=None)
        if not message_date:
            return 0
        age = now - message_date
        if age <= timedelta(days=3):
            return 1
        if age <= timedelta(days=7):
            return 0
        if age <= timedelta(days=14):
            return -1
        return -2

    def _reject(self, reason: str) -> Dict:
        return {
            'is_vacancy': False,
            'specialization': None,
            'detected_keywords': [],
            'relevance_score': 0,
            'budget': None,
            'score_breakdown': {},
            'excluded_specialization': True,
            'excluded_platforms': [],
            'needs_clarification': False,
            'is_agency': False,
            'rejection_reason': reason,
        }
