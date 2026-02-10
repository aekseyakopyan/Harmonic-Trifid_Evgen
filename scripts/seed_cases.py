
import asyncio
from core.database.connection import async_session
from core.database.models import Case
from sqlalchemy import select

cases_data = [
    {
        "title": "Продвижение мобильных купольных домов (Capsule Houses)",
        "category": "Performance Marketing",
        "description": "Маркетинг для производителя мобильных домов-капсул по всей России. Использовался Яндекс.Директ.",
        "results": "Стабильный поток лидов по всей России со средней ценой 1500 руб. за лид.",
        "project_url": "https://teletype.in/@m-marketing/LPhCTen5sV_",
        "image_url": "https://teletype.in/files/5d/7c/5d7c4826-6b60-466d-96f7-873648937000.png"
    },
    {
        "title": "Снижение стоимости лида в строительстве домов",
        "category": "Construction",
        "description": "Кейс по снижению стоимости привлечения клиента для строительной компании с бюджетом 1 млн руб. в месяц.",
        "results": "Стоимость лида снижена до 2000 руб. при сохранении объема заявок.",
        "project_url": "https://teletype.in/@m-marketing/q6OpDe1x-Yj",
        "image_url": "https://teletype.in/files/9a/3b/9a3b2c1d-4e5f-6g7h-8i9j-0k1l2m3n4o5p.jpg" # Placeholder, actual URL might be different
    },
    {
        "title": "Недвижимость СПб и защита от скликивания",
        "category": "Real Estate",
        "description": "Реклама недвижимости в Санкт-Петербурге в условиях жесткой конкуренции и атак ботов.",
        "results": "Цена лида 2000 руб. Внедрена система защиты от скликивания конкурентами.",
        "project_url": "https://teletype.in/@m-marketing/8dRE_0c8rrq",
        "image_url": ""
    },
    {
        "title": "Продвижение премиального мероприятия в бутик-отеле",
        "category": "Events",
        "description": "Привлечение состоятельной аудитории для 5-звездочного отеля и его ресторана.",
        "results": "Успешное заполнение мероприятия целевой аудиторией через Яндекс.Директ и VK.",
        "project_url": "https://teletype.in/@m-marketing/JzJ685j7GUN",
        "image_url": ""
    },
    {
        "title": "Контрактное производство косметики",
        "category": "B2B / Manufacturing",
        "description": "Продвижение услуг контрактного производства (СТМ) косметики.",
        "results": "Качественные B2B лиды по цене 300–700 руб. через Яндекс.Директ.",
        "project_url": "https://teletype.in/@m-marketing/ENVsya3nNLo",
        "image_url": ""
    },
    {
        "title": "Ремонт квартир в СПб (от сарафанки к маркетингу)",
        "category": "Renovation",
        "description": "Перевод компании по ремонту квартир с рекомендаций на системный поток лидов из интернета.",
        "results": "Стоимость лида от 800 руб. Стабильная загрузка бригад.",
        "project_url": "https://teletype.in/@m-marketing/CPcqMtV8crK",
        "image_url": ""
    },
    {
        "title": "Остекление балконов в Краснодаре",
        "category": "Windows / Balconies",
        "description": "Таргетированная реклама услуг по остеклению и отделке балконов.",
        "results": "Лиды от 450 руб. через социальные сети.",
        "project_url": "https://teletype.in/@m-marketing/FRI6sYor0MJ",
        "image_url": ""
    },
    {
        "title": "Магазин напольных покрытий в Москве",
        "category": "Retail / Interior",
        "description": "Комплексный маркетинг и сквозная аналитика для розничного магазина покрытий.",
        "results": "Модернизация привлечения клиентов, рост онлайн-продаж.",
        "project_url": "https://teletype.in/@m-marketing/MNnkGPlaaG1",
        "image_url": ""
    },
    {
        "title": "Кухни и шкафы на заказ в Москве",
        "category": "Furniture",
        "description": "Генерация лидов для производителя мебели в среднем ценовом сегменте.",
        "results": "Стабильный поток заявок на замер из поиска Яндекса по Москве и области.",
        "project_url": "https://teletype.in/@m-marketing/U_EDfW-Y_iT",
        "image_url": ""
    }
]

async def seed():
    async with async_session() as session:
        for data in cases_data:
            # Check if case already exists
            stmt = select(Case).where(Case.project_url == data["project_url"])
            result = await session.execute(stmt)
            if result.scalars().first():
                print(f"Case '{data['title']}' already exists, skipping.")
                continue
                
            case = Case(**data)
            session.add(case)
            print(f"Added case: {data['title']}")
        
        await session.commit()
        print("Seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed())
