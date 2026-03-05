"""
Vacancy Scorer - анализирует сообщения и определяет релевантность вакансии.
"""

import re
import hashlib
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, timezone


class MessageDeduplicator:
    """Fix 10: Дедупликация сообщений по нормализованному тексту"""
    
    def __init__(self, ttl_hours=48):
        self.seen_hashes = {}  # hash → timestamp
        self.ttl = timedelta(hours=ttl_hours)
    
    def is_duplicate(self, text, timestamp=None):
        normalized = re.sub(r'[\U00010000-\U0010ffff]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()[:200]
        text_hash = hashlib.md5(normalized.encode()).hexdigest()
        now = timestamp or datetime.utcnow()
        expired = [h for h, ts in self.seen_hashes.items() if now - ts > self.ttl]
        for h in expired:
            del self.seen_hashes[h]
        if text_hash in self.seen_hashes:
            return True
        self.seen_hashes[text_hash] = now
        return False


class VacancyScorer:
    """Анализатор релевантности вакансий"""
    
    # Ключевые слова для специализаций (ВЫСОКИЙ ПРИОРИТЕТ +3)
    SPECIALIZATIONS = {
        "SEO": {
            "keywords": [
                r"\bseo\b", r"\bсео\b", r"\bсеошник\b",
                r"поисков(?:ая|ую|ой) оптимизаци",
                r"продвижени(?:е|я) сайт",
                r"вывод в топ",
                r"seo[- ]специалист",
                r"оптимизатор",
                r"линкбилдинг", r"linkbuilding",
                r"семантическ(?:ое|ого) ядр",
                r"технический аудит",
                r"органический трафик",
                r"поисковый трафик",
                r"кластеризация", r"перелинковка",
                r"аудит сайта", r"seo-audit",
                r"вывести сайт в поиск", r"поднять сайт в выдаче",
                r"нужно сео", r"нужно seo", r"продвиньте сайт",
                r"\bсеошник\w*\b",
                r"seo[- ]копирайт",
                r"поведенческ\w+\s+фактор",
                r"внешн\w+\s+(?:оптимизаци|ссылк)",
                r"(?:google|гугл)\s+(?:search\s+console|вебмастер)",
                r"яндекс\s+вебмастер",
                r"(?:наращивание|закупка)\s+(?:ссылок|ссылочн)",
                r"(?:title|description|мета[- ]?теги)"
            ],
            "priority": 3
        },
        "контекстная реклама": {
            "keywords": [
                r"контекстн(?:ая|ую|ой) реклам",
                r"яндекс\.директ", r"\bдирект\b",
                r"google ads", r"google adwords",
                r"\bppc\b", r"\bппс\b",
                r"контекстолог", r"директолог",
                r"поисков(?:ая|ую|ой) реклам",
                r"\bрся\b",
                r"\bкмс\b",
                r"настройк(?:а|у) контекст",
                r"ведени(?:е|я) реклам(?:ы)? директ",
                r"оптимизаци(?:я|и) ставок",
                r"реклама в поиске", r"товарная кампания",
                r"контекст под ключ",
                r"запустить директ", r"настроить яндекс",
                r"нужна реклама в яндексе", r"хочу лидов из поиска",
                r"настройте рекламу",
                r"(?:ведение|настройка|оптимизация)\s+(?:рекламн\w+\s+)?кампани[ийя]",
                r"(?:реклама|продвижение)\s+в\s+яндекс",
                r"(?:минус[- ]?слова|минусовка)",
                r"(?:конверси\w+|cpa|cpc|ctr)\s+(?:оптимизаци|улучш)"
            ],
            "priority": 3
        },
        "таргетированная реклама": {
            "keywords": [
                r"таргетирован(?:ная|ную|ой) реклам",
                r"\bтаргет(?:инг)?\b",
                r"таргетолог",
                r"vk ads", r"\bвк реклам",
                r"вконтакте реклам",
                r"вк таргет",
                r"реклама вк",
                r"настройк(?:а|у) таргет(?:а)? вк",
                r"ведени(?:е|я) таргет(?:а)? вк",
                r"lookalike вк", r"лукалайк вконтакте"
            ],
            "priority": 3,
            "platform_check": True  # Требует проверки платформы
        },
        "интернет-маркетинг": {
            "keywords": [
                r"интернет[- ]маркетинг",
                r"digital[- ]маркетинг", r"диджитал[- ]маркетинг",
                r"performance[- ]маркетинг",
                r"\bмаркетолог\b",
                r"трафик[- ]менеджер",
                r"cpa[- ]маркетинг",
                r"привлечени(?:е|я) клиентов",
                r"лидогенераци", r"\bлиды\b",
                r"конверсионн(?:ый|ого) маркетинг",
                r"growth[- ]маркетинг"
            ],
            "priority": 3
        },
        "авито": {
            "keywords": [
                r"\bавито\b", r"\bavito\b",
                r"авитолог",
                r"помощник авитолога",
                r"реклам(?:а|у) (?:на |в )?авито",
                r"размещени(?:е|я) (?:на |в )?авито",
                r"объявлени(?:я|й) (?:на |в )?авито",
                r"продвижени(?:е|я) (?:на |в )?авито",
                r"маспостинг", r"автозагрузка авито",
                r"продажи через авито", r"раскачать авито",
                r"нужны лиды с авито", r"настроить авито",
                r"(?:продвижение|раскрутка|ведение)\s+(?:на\s+)?авито",
                r"(?:авито|avito)\s+(?:про|магазин|кабинет)",
                r"(?:объявлени\w+|карточк\w+)\s+(?:на\s+)?авито"
            ],
            "priority": 3
        }
    }
    
    # СРЕДНИЙ ПРИОРИТЕТ (+2)
    SPECIALIZATIONS_MEDIUM = {
        "разработка сайтов": {
            "keywords": [
                r"\btilda\b", r"\bтильда\b",
                r"разработ(?:ка|ку) сайт",
                r"\bлендинг\b", r"landing page",
                r"одностраничник",
                r"создани(?:е|я) сайт",
                r"посадочн(?:ая|ую) страниц",
                r"сайт под ключ",
                r"readymag", r"webflow",
                r"хочу сайт", r"нужен сайт", r"сделать сайт",
                r"помогите с сайтом", r"кто делает сайты",
                r"нужен лендинг", r"собрать сайт",
                r"\bcms\b",
                r"(?:доработка|переделка|редизайн)\s+сайт",
                r"\bflexbe\b", r"\bкрафтум\b", r"\bcraftum\b",
                r"(?:opencart|опенкарт|woocommerce|вукомерс)",
                r"(?:адаптивн\w+\s+(?:верстк|дизайн))",
                r"(?:интеграци\w+)\s+(?:с\s+)?(?:crm|1с|битрикс|амо)",
                r"\bсайтолог\b", r"\bтильдолог\b"
            ],
            "priority": 2
        },
        "веб-дизайн": {
            "keywords": [
                r"веб[- ]дизайн", r"web[- ]дизайн",
                r"ui/ux дизайн",
                r"дизайн сайт",
                r"дизайн лендинг",
                r"прототипирование",
                r"figma дизайн",
                r"адаптивн(?:ый|ого) дизайн",
                r"(?:макет|прототип)\s+(?:сайта|лендинга|страниц)",
                r"(?:дизайн|редизайн)\s+(?:интернет[- ]?магазин|сайт|лендинг|страниц)",
                r"(?:figma|фигма)\s+(?:макет|дизайн|прототип)"
            ],
            "priority": 2
        },
    }
    
    # ИСКЛЮЧЕННЫЕ СПЕЦИАЛИЗАЦИИ (полностью отклоняем)
    EXCLUDED_SPECIALIZATIONS = [
        r"\bsmm\b", r"\bсмм\b",
        r"smm[- ]специалист",
        r"social media",
        r"контент[- ]менеджер", r"контент[- ]мейкер",
        r"email[- ]маркетинг", r"email[- ]рассылк",
        # Копирайтинг исключаем, НО не SEO-копирайтинг
        r"(?<!seo[- ])копирайтер", r"(?<!seo[- ])копирайтинг",
        r"редактор", r"корректор",
        r"ассистент", r"помощник",
        r"(?<!digital[- ])маркетолог", r"продуктовый маркетолог", r"product marketing",
        r"маркетинговый копирайтинг",
        r"продающ(?:ие|их) текст",
        r"коммерческ(?:ие|их) текст",
        r"текст(?:ы|ов) для реклам",
        r"lsi[- ]копирайтинг",
        r"текст(?:ы|ов) для лендинг",
        r"аналитик", r"анализ данных",
        r"\bcrm\b", r"crm[- ]менеджер", r"crm[- ]маркетолог",
        # Дизайн и визуал
        r"графический дизайнер", 
        r"моушн[- ]дизайнер", r"motion designer",
        r"видеокреатор", r"видео[- ]монтаж", r"монтажер",
        r"рилсмейкер", r"reels", r"shorts",
        r"сторисмейкер", r"stories maker",
        r"художник", r"2d артист", r"2d artist", r"иллюстратор",
        r"фотограф", r"фотошоп[- ]мастер",
        r"менеджер по продажам", r"сейлз", r"sales manager",
        r"холодные звонки", r"оператор колл-центра",
        r"hr[- ]менеджер", r"рекрутер", r"подбор персонала"
    ]

    # ИСКЛЮЧЕННЫЕ ЛОКАЦИИ (полностью отклоняем)
    EXCLUDED_LOCATIONS = [
        r"алмат[ыа]", r"казахстан", r"казахстан[аеу]",
        r"алма[- ]ат[ыа]", r"астана", r"узбекистан", r"ташкент",
        r"грузия", r"тбилиси", r"ереван", r"армения"
    ]
    
    # ИСКЛЮЧЕННЫЕ ПЛАТФОРМЫ для таргета
    EXCLUDED_PLATFORMS = [
        r"tg ads", r"telegram ads", r"реклам(?:а|у) в телеграм",
        r"mytarget", r"майтаргет",
        r"facebook ads", r"meta ads", r"fb ads",
        r"instagram ads", r"реклам(?:а|у) в инстаграм"
    ]
    
    # Индикаторы вакансии (+2)
    VACANCY_INDICATORS = [
        r"\bищу\b", r"\bищем\b",
        r"\bнужен\b", r"\bнужна\b", r"\bнужны\b",
        r"\bтребуется\b", r"\bтребуются\b",
        r"\bвакансия\b", r"\bvacancy\b",
        r"\bhiring\b", r"\bhire\b",
        r"кто может", r"кто умеет",
        r"есть кто",
        r"помогите найти",
        r"\bнабираем\b",
        r"\bприглашаем\b",
        r"рассматриваем кандидатов",
        r"ищу подрядчика",
        r"нужен специалист",
        r"срочно нужен",
        r"кто возьмется",
        r"кто готов",
        r"ищу фрилансера",
        r"требуется исполнитель",
        r"в штат", r"ищу в штат",
        r"подрядчик", r"ищу подрядчика",
        r"закрыть задачу", r"помогите закрыть",
        r"откликнуться", r"заполнить анкет", r"заполнить форму",
        r"ищу того кто", r"нужен человек который",
        r"кто может реализовать", r"запустить проект",
        # Новые индикаторы (P1)
        r"📌\s+\w",                           # Маркер заказа Kwork/биржи
        r"🔥\s*(?:заказ|срочн)",               # Срочный заказ Tilda Profi
        r"связаться с заказчиком",             # Kwork
        r"freelancehunt\.com/project",         # Ссылки Freelancehunt
        r"freelance\.ua/orders",               # Ссылки freelance.ua
        r"kwork\.ru/projects",                 # Ссылки Kwork
        r"finder\.work/vacancies",             # Ссылки finder.work
        r"hh\.ru/vacancy",                     # HeadHunter
        r"🙋[‍♂️♀️]*\s",                        # Маркер заказчика
        r"от\s+\d+[\s,]*\d*\s*(?:до|₽|руб)",  # Вилка зарплаты
    ]
    
    # Признаки АГЕНТСТВА (блокирующий фактор -10)
    AGENCY_PATTERNS = [
        r"в (?:нашу )?команд(?:у|е).{0,50}агентств",
        r"в (?:нашу )?команд(?:у|е).{0,50}студи",
        r"ищ(?:у|ем) в команд",
        r"набираем команд",
        r"расширяем команд",
        r"ищ(?:у|ем) в агентств",
        r"требуется в команд(?:у)? агентств",
        r"smm[- ]агентств(?:о|а) ищ",
        r"digital[- ]агентств(?:о|а) ищ",
        r"маркетинговое агентств"
    ]
    
    # "В команду" без агентства (требует уточнения)
    TEAM_PATTERNS = [
        r"ищ(?:у|ем) в команд",
        r"расширяем команд",
        r"набираем команд",
        r"требуется в команд"
    ]
    
    # Признаки СПАМА (эфиры, курсы, рекламные посты) - блокирующий
    SPAM_PATTERNS = [
        r"прикладной эфир", r"полезный эфир", r"зайти на эфир",
        r"записаться на эфир", r"бесплатн(?:ый|ого) эфир",
        r"прогрев(?:а)? к курс", r"продаж(?:а|и) курс",
        r"обнял, приподнял", r"шлепнул по жопке",
        r"как зарабатывать \d+\.?\d* (?:тысяч|рубл)",
        r"пройди бесплатное обучение",
        r"насмотренность.*видео.*контента",
        r"стань режиссером", r"нейросети в кино",
        r"подпишись на канал", r"вступай в группу",
        r"крипта", r"p2p", r"арбитраж трафика", r"темки",
        r"абуз", r"реферальная ссылка", r"переходи по ссылке",
        r"дарю чек-лист", r"скачать гайд", r"забирай подарок",
        r"пассивный доход", r"удаленный заработок для всех",
        r"требуются люди для перепечатки", r"обработка текста на дому",
        r"выплаты ежедневно", r"без вложений",
        r"халява", r"раздача денег", r"розыгрыш",
        r"подработка для студентов", r"легкие деньги",
        r"заработок в приложении", r"тапать", r"хомяк",
        r"занимаюсь\s+составлением",
        r"системные\s+продажи",
        r"вернуть\s+себе\s+время",
        r"коллеги,?\s*(?:кто\s+хочет|устали|хочу\s+предложить)",
        r"аккаунт(?:ы)?(?:\s+(?:в\s+)?авито)?.*\s+отзыв(?:ам|ами|ах)?",
        r"написани(?:я|е)\s+отзывов",
        "отзывы за деньги",
        "купить отзывы",
        r"event[- ]агентств",
        r"маркетингово(?:е|м)\s+агентств",
        r"занимаюсь\s+посевами",
        r"сделаю\s+посевы",
        r"коротк(?:ие|их)\s+ролик(?:и|ов)",
        r"reels|рилс|риллс|shorts",
        r"клониров(?:ать|ание)\s+голос(а)?",
        r"вебинар", r"приглашаем\s+на\s+(?:семинар|вебинар)",
        r"АСУТП", r"промышленн(?:ые|ую)\s+автоматизаци",
        # Fix 11: Новые спам-паттерны
        r"массовая?\s+рассылк[аи]",
        r"(?:рассылк[аи]|инвайтинг|парсинг).{0,30}(?:telegram|тг|tg)",
        r"(?:софт|бот)\s+(?:для\s+)?(?:рассылк|парсинг|инвайтинг)",
        r"оператор\s+(?:онлайн[- ])?чата",
        r"международн\w+\s+(?:онлайн[- ])?школ",
        r"присоединяйтесь\s+к\s+нашему\s+(?:международн|чат)",
        # Украинский язык
        r"[єґіїІЇ]", r"\bщо\b", r"\bта\s+(?:й|її|він|вона)\b", r"\bякщо\b"
    ]
    
    # Признаки "ПРЕДЛОЖЕНИЯ УСЛУГ" (блокируем, так как нам нужны запросы)
    OFFER_PATTERNS = [
        r"ищ(?:у|ем)\s+(?:работу|заказы|проекты|клиентов|подработку)",
        r"предлагаю(?: свои)? услуги",
        r"выполню\s+(?:работу|заказ|настройку)",
        r"готов(?:а)?\s+(?:взять|выполнить|работать)",
        r"портфолио:", r"мои кейсы", r"опыт работы:",
        r"в поиске\s+(?:работы|заказов|проектов)",
        r"сделаю на совесть", r"настрою под ключ",
        r"пишите в лс для заказа", r"открыт(?:а)? к предложениям",
        # Новые паттерны из анализа ИИ
        r"отзыв(?:ы|ов)\s+на\s+авито", r"верификаци(?:я|и)\s+на\s+авито",
        r"аккаунт(?:ы|ов)\s+авито", r"аренду\s+аккаунт",
        r"менеджер(?:ы)?-помощниц(?:ы)?\s+для\s+авито",
        r"без\s+(?:будильника|начальника|вложений)",
        r"выплата\s+на\s+следующий\s+день", r"копипастом",
        r"международную\s+онлайн-\s*школу", r"научим\s+зарабатывать",
        r"продюсер\s+(?:стратег|маркетолог)", r"меня\s+зовут\s+(?:Алена|Алёна)",
        r"помогу\s+с\s+(?:продажами|продвижением|маркетингом|таргетом|SEO)",
        r"подработка\s+для\s+телефон", r"обучение\s+работе\s+с\s+нуля",
        # Дополнительно из финального анализа
        r"отзыв(?:ы|ов)(?:\s+на)?\s+авито", r"оператор\s+чата\s+на\s+авито",
        r"простые\s+задания\s+на\s+биржах", r"(?:канал|инструкцию)\s+по\s+заработку",
        r"доход\s+ежедневно", r"выплата\s+раз\s+в\s+неделю",
        r"стать\s+оператором\s+авито", r"хочу\s+быть\s+оператором",
        # Новые паттерны: самопрезентации и предложения "сделаю"
        r"(?:привет|здравствуйте|всех приветст?вую).{0,20}меня\s+зовут",
        r"меня\s+зовут\s*[–-]?\s*[А-Я][а-я]+", 
        r"я\s+сертифицированн(?:ый|ая)",
        r"(?:сделаю|настрою|разработаю|создам|создаю|делаю)\s+(?:как\s+)?(?:для\s+вас\s+)?(?:чат[- ]?бота|ии[- ]?агента|сайт|веб[- ]?сайт|сео|seo|карточк(?:и|ек))",
        r"аудит\s+безопасности\s+сайта",
        r"кому\s+нужны\s+клиенты",
        r"оплата\s+(?:до\s+и\s+после|после\s+получения)",
        r"карточк(?:и|ек)\s+для\s+мп",
        r"беру.{0,10}проект(?:а|ов)(?:\s+на\s+запуск)?",
        r"занимаюсь\s+составлением",
        r"возьму\s+в\s+работу",
        r"коллеги,?\s*(?:кто\s+хочет|устали|хочу\s+предложить)",
        r"могу\s+помочь\s+с",
        r"разработки?\s+любой\s+сложности",
        r"последнее\s+время\s+(?:часто\s+)?вижу",
        # Fix 9: Новые offer-паттерны
        r"#(?:фрилансер|исполнитель|разработчик|дизайнер|верстальщик)\b",
        r"(?:привет|здравствуйте)[!.\s]*(?:я\s+(?:веб|дизайн|маркетолог|фрилансер|специалист))",
        r"(?:привет|здравствуйте)[!.\s]*(?:предлагаю|меня\s+зовут)",
        r"(?:предлагаю|выполню|сделаю|настрою|разработаю|создам|соберу)\s+(?:для\s+вас|вам|под\s+ключ|качественн)",
        r"(?:более|больше|свыше|от)\s+\d+\s+(?:(?:реализованных\s+)?проектов|(?:успешных\s+)?кейсов|лет\s+(?:в|опыт))",
        r"(?:бесплатн\w+)\s+(?:аудит|консультаци|разбор|стратеги)",
        r"(?:со\s+скидкой|акция|спецпредложение|спец\.?\s*цена)",
        r"(?:готов(?:а)?)\s+(?:взять|выполнить|приступить|начать|стартовать)",
        r"(?:открыт(?:а)?|свободен|доступен|доступна)\s+(?:для|к)\s+(?:новых?|сотрудничеств|проект|заказ)",
        r"(?:нахожусь|я)\s+в\s+поиске\s+(?:новых?\s+)?(?:клиентов|заказов|проектов)",
        r"(?:приведу|привлеку|привлечем|приведём)\s+(?:в\s+ваш|вам|новых?)\s+(?:бизнес|компани|клиент)",
        r"(?:мой|моя|мои|моё)\s+(?:портфолио|кейс|работ|опыт)",
        r"(?:возьму|беру|принимаю)\s+(?:в\s+работу|на\s+(?:проект|аутсорс)|заказ)",
        r"(?:гарантирую|гарантия)\s+(?:результат|возврат|качеств)",
    ]
    
    # Другие исключения (-3)
    OTHER_EXCLUSIONS = [
        r"\bjunior\b", r"джуниор", r"начинающий",
        r"стажер", r"стажировк", r"\bintern\b",
        r"без опыта",
        r"\bзакрыто\b", r"\bнашли\b", r"исполнитель найден",
        r"вакансия закрыта"
    ]
    
    # Индикаторы прямого обращения или вопроса (+3)
    CONTEXT_INDICATORS = [
        r"посоветуйте", r"рекомендуйте", r"подскажите", r"знает ли кто",
        r"нужна помощь", r"кто делал", r"кто может сделать", r"ищу специалиста",
        r"есть контакты", r"дайте контакт", r"кто занимается", r"нужна консультация",
        # Новые контекстные индикаторы (P1)
        r"заказ\s*#\d+",                       # Номер заказа
        r"бюджет:",                            # Указание бюджета
        r"дедлайн:",                           # Указание сроков
        r"ТЗ:",                                # Техзадание
    ]

    def __init__(self):
        from core.config.settings import settings
        import json
        import os
        self.all_specializations = {**self.SPECIALIZATIONS, **self.SPECIALIZATIONS_MEDIUM}
        self.target_keywords = [k.strip().lower() for k in settings.TARGET_KEYWORDS.split(",") if k.strip()]
        self.deduplicator = MessageDeduplicator(ttl_hours=48)
        
        # Загрузка динамических фильтров
        self.dynamic_filters = {"positive": [], "negative": []}
        dynamic_path = os.path.join(os.path.dirname(__file__), "../../../core/config/dynamic_filters.json")
        if os.path.exists(dynamic_path):
            try:
                with open(dynamic_path, 'r', encoding='utf-8') as f:
                    self.dynamic_filters = json.load(f)
            except Exception as e:
                print(f"Error loading dynamic filters: {e}")
    
    def analyze_message(self, text: str, message_date: datetime = None) -> Dict:
        """
        Метод анализа сообщения. Теперь ищет и вакансии, и лиды по ключевым словам.
        """
        text_lower = text.lower()
        
        # Fix 10: Дедупликация
        if self.deduplicator.is_duplicate(text, message_date):
            return self._negative_result("Дубликат")
        
        # 0. Проверка на спам (эфиры, курсы, промо) - ПЕРВООЧЕРЕДНО
        if self._is_spam(text_lower):
            return self._negative_result("Рекламный/промо контент")
            
        # ПРОВЕРКА НА ИЗБЫТОК ЭМОДЗИ (часто спам/офферы)
        emoji_count = len(re.findall(r"[\U00010000-\U0010ffff]", text))
        if emoji_count > 25:
            return self._negative_result(f"Избыток эмодзи ({emoji_count})")
        
        # Мягкий штраф за эмодзи
        emoji_penalty = -1 if emoji_count > 15 else 0

        # 0.1 Проверка на ПРЕДЛОЖЕНИЕ услуг (нам нужны только запросы)
        if self._is_offer(text_lower):
            return self._negative_result("Предложение услуг (Sellers)")

        # 1. Детекция специализации (Fix 1: Перенесено выше)
        specialization, spec_score, keywords = self._detect_specialization(text_lower)
        keyword_match = self._check_target_keywords(text_lower)
        
        if not specialization and keyword_match:
            specialization = "Keyword Match"
            spec_score = 3
            keywords = [keyword_match]

        # 2. Проверка на блокируемые роли (Fix 1: Только если спец-я не найдена)
        # Убраны ^#ищу, #помогу, маркетолог
        blocked_role_pattern = r"помощник|ассистент|(?<!seo[- ])автор|(?<!seo[- ])редактор|(?<!seo[- ])копирайтер|бизнесассистент|сценарист|продюсер|продюссер|администратор|smm|смм|техспец|куратор|продажник|менеджер по продажам|sales manager|эксперт|таргетолог|таргет|facebook|instagram|фейсбук|инстаграм|(?<!\w)fb(?!\w)|(?<!\w)ig(?!\w)|event[- ]агентство|маркетинговое агентство|аккаунт.*авито|отзыв(?:ы|ов).*авито|посев(?:ы|ам)|коротк(?:ие|их) ролик(?:и|ов)|reels|рилс|риллс|shorts|клониров(?:ать|ание) голос(а)?|татьяна мелехова|сертифицированн|#услуги|#сценарист|#продюсер|#продюссер|#резюме|#ищуработу"
        is_blocked_role = re.search(blocked_role_pattern, text_lower, re.IGNORECASE)
        
        if is_blocked_role and not specialization:
            return self._negative_result(f"Исключено: Блокируемая роль ({is_blocked_role.group(0)})")

        # 3. Детекция типа лида (Fix 12: добавлен order_format_score)
        vacancy_score = self._detect_vacancy_indicators(text_lower)
        context_score = self._detect_context_indicators(text_lower)
        order_format_score = self._detect_order_format(text_lower)
        
        demand_score = max(vacancy_score, context_score)
        
        # Fix 12+14: Требуем хотя бы один «якорь» — demand ИЛИ формат заказа
        if demand_score == 0 and order_format_score == 0 and not specialization:
            return self._negative_result("Нет demand-сигнала и не формат заказа")
        
        # 4. Проверка исключенных специализаций (только если спец-я не признана целевой)
        if self._is_excluded_specialization(text_lower) and not specialization:
            return self._negative_result("Исключенная специализация (SMM/Email/Analyst/CRM)")
        
        # 5. Проверка исключенных локаций
        excluded_location = self._check_excluded_locations(text_lower)
        if excluded_location:
            return self._negative_result(f"Исключенная локация: {excluded_location}")
        
        if not specialization:
             return self._negative_result("Специализация не определена")
        
        # 6. Проверка на агентство (Fix 5: Пропускать если есть специализация)
        agency_check = self._check_agency(text_lower)
        if agency_check['is_agency'] and not specialization:
            return self._negative_result("Вакансия/Запрос в агентство", agency_check=agency_check)
        
        # 7. Дополнительные бонусы
        remote_bonus = 1 if self._detect_remote_work(text_lower) else 0
        budget_text = self._extract_budget(text)
        budget_bonus = 1 if budget_text else 0
        freshness_bonus = self._calculate_freshness_bonus(message_date) if message_date else 0
        
        # Проверка других исключений
        exclusion_penalty = self._check_other_exclusions(text_lower)
        
        # Финальный расчет (Fix 12: используем max из demand и order_format)
        total_score = (
            max(demand_score, order_format_score) + 
            spec_score +
            remote_bonus +
            budget_bonus +
            freshness_bonus +
            exclusion_penalty +
            emoji_penalty
        )
        
        return {
            'is_vacancy': total_score >= 3,
            'specialization': specialization,
            'detected_keywords': keywords,
            'relevance_score': total_score,
            'budget': budget_text,
            'score_breakdown': {
                'vacancy_indicators': vacancy_score,
                'context_indicators': context_score,
                'specialization_match': spec_score,
                'remote_work': remote_bonus,
                'budget_mentioned': budget_bonus,
                'freshness': freshness_bonus,
                'exclusions_penalty': exclusion_penalty,
                'emoji_penalty': emoji_penalty
            },
            'excluded_specialization': False,
            'excluded_platforms': [],
            'needs_clarification': agency_check.get('needs_clarification', False),
            'is_agency': False
        }

    def _detect_context_indicators(self, text: str) -> int:
        """Поиск контекстных сигналов (вопросы, советы). Возвращает +3."""
        for pattern in self.CONTEXT_INDICATORS:
            if re.search(pattern, text, re.IGNORECASE):
                return 3
        return 0

    def _check_target_keywords(self, text: str) -> Optional[str]:
        """Точная проверка по вашему списку ключевых слов из настроек + динамические позитивы."""
        # 1. Из settings.TARGET_KEYWORDS
        for kw in self.target_keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                return kw
                
        # 2. Динамически выученные позитивы
        for pattern in self.dynamic_filters.get("positive", []):
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
                
        return None
    def _detect_vacancy_indicators(self, text: str) -> int:
        """Поиск индикаторов вакансии. Возвращает +2 если найдено."""
        for pattern in self.VACANCY_INDICATORS:
            if re.search(pattern, text, re.IGNORECASE):
                return 2
        return 0
    
    def _detect_specialization(self, text: str) -> Tuple[str, int, List[str]]:
        """
        Определяет специализацию и возвращает (название, балл, ключевые слова).
        """
        best_match = None
        best_score = 0
        matched_keywords = []
        
        for spec_name, spec_data in self.all_specializations.items():
            matches = []
            for keyword in spec_data['keywords']:
                if re.search(keyword, text, re.IGNORECASE):
                    matches.append(keyword)
            
            if matches:
                score = spec_data['priority']
                if score > best_score or (score == best_score and len(matches) > len(matched_keywords)):
                    best_match = spec_name
                    best_score = score
                    matched_keywords = matches
        
        return best_match, best_score, matched_keywords
    
    def _is_excluded_specialization(self, text: str) -> bool:
        """Проверка на исключенные специализации."""
        for pattern in self.EXCLUDED_SPECIALIZATIONS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _check_excluded_locations(self, text: str) -> str:
        """Проверка на исключенные локации. Возвращает название локации если найдено."""
        for pattern in self.EXCLUDED_LOCATIONS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def _is_spam(self, text: str) -> bool:
        """Проверка на рекламный/промо контент + динамические негативы."""
        # 1. Жесткие паттерны в коде
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # 2. Обученные негативы от Гвен
        for pattern in self.dynamic_filters.get("negative", []):
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        return False

    def _check_excluded_platforms(self, text: str) -> List[str]:
        """Проверка исключенных платформ для таргета."""
        found = []
        for pattern in self.EXCLUDED_PLATFORMS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern)
        return found
    
    def _check_agency(self, text: str) -> Dict:
        """
        Проверка на агентство.
        """
        # Проверка явного упоминания агентства
        for pattern in self.AGENCY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    'is_agency': True,
                    'needs_clarification': False,
                    'reason': 'Явное упоминание агентства'
                }
        
        # Проверка "в команду" без агентства
        for pattern in self.TEAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Проверяем, есть ли упоминание агентства рядом
                if not re.search(r"агентств|студи", text, re.IGNORECASE):
                    return {
                        'is_agency': False,
                        'needs_clarification': True,
                        'reason': 'В команду без явного упоминания агентства'
                    }
        
        return {
            'is_agency': False,
            'needs_clarification': False
        }
    
    def _check_other_exclusions(self, text: str) -> int:
        """Проверка других исключений. Возвращает -3 за каждое."""
        penalty = 0
        for pattern in self.OTHER_EXCLUSIONS:
            if re.search(pattern, text, re.IGNORECASE):
                penalty -= 3
        return penalty
    
    def _detect_remote_work(self, text: str) -> bool:
        """Детектор удаленной работы."""
        patterns = [
            r"\bудаленно\b", r"удалённка", r"\bremote\b",
            r"из любой точк", r"работа на дом"
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _extract_budget(self, text: str) -> str:
        """Извлекает сумму бюджета из текста."""
        # Паттерны для поиска сумм (от 20к до 1ляма)
        patterns = [
            r"(?:от|до|–|-|—|\s)(\d{1,3}(?:\s?\d{3})?)\s?(?:₽|руб|р\.|т\.р\.|тыс|k|к|usd|\$|euro|€)(?!\w)",
            r"(?:оплата|бюджет|зп|доход|ставка):?\s?(\d{1,3}(?:\s?\d{3})?)\s?(?:₽|руб|р\.|т\.р\.|тыс|k|к|usd|\$|euro|€)?(?!\w)",
            r"(\d{1,3}(?:\s?\d{3})?)\s?-\s?(\d{1,3}(?:\s?\d{3})?)\s?(?:₽|руб|р\.|т\.р\.|тыс|k|к|usd|\$|euro|€|net|gross)?(?!\w)"
        ]
        
        all_matches = []
        for p in patterns:
            matches = re.finditer(p, text, re.IGNORECASE)
            for m in matches:
                all_matches.append(m.group(0).strip())
        
        return ", ".join(all_matches) if all_matches else None

    def _detect_budget(self, text: str) -> bool:
        """Детектор упоминания бюджета (устаревший, используется для бонуса)."""
        return bool(self._extract_budget(text))
    
    def _calculate_freshness_bonus(self, message_date: datetime) -> int:
        """Расчет бонуса за свежесть."""
        if not message_date:
            return 0
        
        # Приводим к naive UTC для корректного вычитания
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if message_date.tzinfo:
            message_date = message_date.replace(tzinfo=None)
            
        age = now - message_date
        
        if age <= timedelta(days=3):
            return 1
        elif age <= timedelta(days=7):
            return 0
        elif age <= timedelta(days=14):
            return -1
        else:
            return -2
    
    def _negative_result(self, reason: str, agency_check: Dict = None) -> Dict:
        """Формирует отрицательный результат."""
        return {
            'is_vacancy': False,
            'specialization': None,
            'detected_keywords': [],
            'relevance_score': 0,
            'score_breakdown': {},
            'excluded_specialization': True,
            'excluded_platforms': [],
            'needs_clarification': agency_check.get('needs_clarification', False) if agency_check else False,
            'is_agency': agency_check.get('is_agency', False) if agency_check else False,
            'rejection_reason': reason
        }
    def _is_offer(self, text: str) -> bool:
        """Проверка на предложение услуг (Sellers). Fix 9: demand override."""
        # Если есть сильный demand-сигнал — НЕ считать оффером
        demand_overrides = [
            r"\bтребуется\b", r"\bтребуются\b", r"\bвакансия\b",
            r"(?:срочно\s+)?нуж(?:ен|на|ны)\b",
            r"\bищу\b", r"\bищем\b",
            r"📌\s+\w", r"заказ\s*#\d+",
            r"связаться с заказчиком",
        ]
        for pattern in demand_overrides:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        for pattern in self.OFFER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_order_format(self, text: str) -> int:
        """Fix 12: Детектор формата заказа (Kwork, Tilda Profi, биржи). Возвращает +2."""
        order_patterns = [
            r"📌\s+\w",
            r"🔥\s*(?:заказ|срочн)",
            r"связаться с заказчиком",
            r"заказ\s*#\d+",
            r"freelancehunt\.com/project",
            r"freelance\.ua/orders",
            r"kwork\.ru/projects",
            r"finder\.work/vacancies",
            r"hh\.ru/vacancy",
        ]
        for pattern in order_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 2
        return 0
