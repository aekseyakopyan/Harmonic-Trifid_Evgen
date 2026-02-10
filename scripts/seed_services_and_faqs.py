
import asyncio
from sqlalchemy import select
from core.database.connection import async_session
from core.database.models import Service, FAQ

async def seed_data():
    async with async_session() as session:
        # 1. Services
        services = [
            {
                "name": "SEO-продвижение",
                "description": "Комплексное продвижение сайтов в Яндекс и Google. Упор на техническую оптимизацию, качественный контент и ссылочный профиль.",
                "price_range": "40 000 - 80 000 руб/мес",
                "process": "1. Аналитический этап (аудит, конкуренты)\n2. Техническая оптимизация (исправление ошибок)\n3. Наполнение контентом и семантика\n4. Внешнее продвижение (ссылки)\n5. Поведенческие факторы (опционально)",
                "timeline": "Первые результаты через 3 месяца, стабильный рост через 6-12 месяцев"
            },
            {
                "name": "Контекстная реклама (Яндекс.Директ)",
                "description": "Привлечение целевого трафика с оплатой за клики или конверсии. Настройка Поиска, РСЯ и Ретаргетинга.",
                "price_range": "40 000 руб/мес (за работу) + бюджет",
                "process": "1. Аудит текущих кампаний\n2. Настройка целей и аналитики\n3. Сбор семантики и запуск объявлений\n4. Ежедневная оптимизация и масштабирование",
                "timeline": "Запуск за 3-5 рабочих дней"
            },
            {
                "name": "Разработка сайтов",
                "description": "Создание профессиональных сайтов на WordPress или Tilda. Полная адаптивность, высокая скорость и SEO-подготовка.",
                "price_range": "от 140 000 руб",
                "process": "1. Брифинг и ТЗ\n2. Прототипирование и дизайн\n3. Верстка и программирование\n4. Наполнение контентом\n5. Тестирование и запуск",
                "timeline": "6-8 недель"
            },
            {
                "name": "Продвижение на Авито",
                "description": "Масштабирование продаж через доску объявлений Авито. Оформление магазина, масс-постинг и работа с отзывами.",
                "price_range": "от 35 000 руб/мес",
                "process": "1. Анализ ниши и конкурентов\n2. Создание стратегии размещения\n3. Подготовка контента и фото\n4. Автоматизация постинга и работа с ПФ",
                "timeline": "Старт за 1 неделю"
            }
        ]

        for s_data in services:
            stmt = select(Service).where(Service.name == s_data["name"])
            result = await session.execute(stmt)
            existing = result.scalars().first()
            if not existing:
                print(f"Adding service: {s_data['name']}")
                session.add(Service(**s_data))
            else:
                print(f"Updating service: {s_data['name']}")
                for key, value in s_data.items():
                    setattr(existing, key, value)

        # 2. FAQs
        faqs = [
            {
                "question": "Какие гарантии вы даете?",
                "answer": "Мы фиксируем в договоре конкретные показатели: рост позиций, органического трафика или стоимости лида. На каждый проект выделяется не более 7 заказов на одного SEO-специалиста для максимального погружения.",
                "category": "General"
            },
            {
                "question": "Почему SEO стоит так дорого?",
                "answer": "В стоимость входят работы SEO-специалиста, программиста, копирайтера, а также бюджет на закупку качественных ссылок и сервисы аналитики. Мы делаем упор на качество, которое приносит результат в долгосроке.",
                "category": "SEO"
            },
            {
                "question": "Как быстро я увижу первые продажи с рекламы?",
                "answer": "Контекстная реклама начинает приносить трафик сразу после прохождения модерации (обычно 1-3 дня). Первые продажи можно получить уже в первую неделю работы.",
                "category": "Ads"
            },
            {
                "question": "Что нужно от меня для начала работы?",
                "answer": "Для старта нужен заполненный бриф и доступы к текущим системам аналитики (если есть). Мы ценим активное участие клиента, так как вы лучше всех знаете свой продукт.",
                "category": "General"
            }
        ]

        for f_data in faqs:
            stmt = select(FAQ).where(FAQ.question == f_data["question"])
            result = await session.execute(stmt)
            existing = result.scalars().first()
            if not existing:
                print(f"Adding FAQ: {f_data['question']}")
                session.add(FAQ(**f_data))
            else:
                print(f"Updating FAQ: {f_data['question']}")
                for key, value in f_data.items():
                    setattr(existing, key, value)

        await session.commit()
        print("Seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed_data())
