import asyncio
from core.database.connection import async_session, init_db
from core.database.models import Case, Service, FAQ

async def seed_data():
    print("Initializing database...")
    await init_db()
    
    print("Seeding initial data...")
    
    async with async_session() as session:
        # 1. Initial Cases
        cases = [
            Case(
                title="SEO продвижение интернет-магазина электроники",
                category="SEO",
                description="Рост органического трафика на 150% за 6 месяцев.",
                results="Увеличение конверсии в 2 раза, вывод 50+ запросов в ТОП-3.",
                project_url="https://example.com/case-seo"
            ),
            Case(
                title="Разработка корпоративного портала для логистической компании",
                category="Development",
                description="Создание сложной системы управления заказами на React + Python.",
                results="Оптимизация внутренних процессов на 30%, поддержка 1000+ активных пользователей.",
                project_url="https://example.com/case-dev"
            ),
            Case(
                title="Эффективная контекстная реклама для службы доставки",
                category="Ads",
                description="Настройка Яндекс.Директ и Google Ads.",
                results="Снижение стоимости лида (CPL) на 40%, увеличение объема заказов на 60%.",
                project_url="https://example.com/case-ads"
            )
        ]
        
        # 2. Initial Services
        services = [
            Service(
                name="SEO Продвижение",
                description="Комплексное поисковое продвижение сайтов.",
                price_range="от 50 000 руб. / мес.",
                process="Аудит -> Стратегия -> Оптимизация -> Ссылочное -> Аналитика",
                timeline="3-12 месяцев"
            ),
            Service(
                name="Разработка сайтов",
                description="Создание сайтов любой сложности: от лендингов до систем.",
                price_range="от 100 000 руб.",
                process="Брифинг -> Дизайн -> Разработка -> Тестирование -> Запуск",
                timeline="1-4 месяца"
            )
        ]

        # 3. FAQs
        faqs = [
            FAQ(
                question="Сколько стоит SEO?",
                answer="Наши тарифы на SEO начинаются от 50 000 рублей в месяц и зависят от масштаба проекта.",
                category="SEO"
            ),
            FAQ(
                question="Как долго делается сайт?",
                answer="Обычно разработка занимает от 1 до 4 месяцев в зависимости от сложности.",
                category="Development"
            )
        ]

        session.add_all(cases)
        session.add_all(services)
        session.add_all(faqs)
        await session.commit()
        print("Data seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed_data())
