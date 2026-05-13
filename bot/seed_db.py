import asyncio
from db.database import async_session, init_db
from services.crud import create_user
from services.raitings import recalculate_user_rating

async def seed_data():
    print("🚀 Наполняю базу тестовыми анкетами...")
    await init_db()
    
    test_users = [
        # Девушки (для теста, если ты зарегаешься как Парень)
        {
            'telegram_id': 1001,
            'full_name': 'Мария',
            'age': 22,
            'gender': 'Девушка',
            'city': 'Москва',
            'bio': 'Люблю кофе, программирование и долгие прогулки. Ищу единомышленников!'
        },
        {
            'telegram_id': 1002,
            'full_name': 'Анна',
            'age': 19,
            'gender': 'Девушка',
            'city': 'Санкт-Петербург',
            'bio': 'Художница, рисую портреты. Хочу найти кого-то особенного.'
        },
        {
            'telegram_id': 1003,
            'full_name': 'Елена',
            'age': 25,
            'gender': 'Девушка',
            'city': 'Москва',
            'bio': 'Занимаюсь спортом, бегаю по утрам. Давай побегаем вместе?'
        },
        {
            'telegram_id': 1004,
            'full_name': 'Виктория',
            'age': 21,
            'gender': 'Девушка',
            'city': 'Казань',
            'bio': 'Путешествия — моя страсть. Была в 10 странах!'
        },
        # Парни (для теста, если ты зарегаешься как Девушка)
        {
            'telegram_id': 2001,
            'full_name': 'Александр',
            'age': 24,
            'gender': 'Парень',
            'city': 'Москва',
            'bio': 'Backend разработчик на Python. Люблю сложные задачи.'
        },
        {
            'telegram_id': 2002,
            'full_name': 'Дмитрий',
            'age': 27,
            'gender': 'Парень',
            'city': 'Новосибирск',
            'bio': 'Играю на гитаре, пою в группе. Ищу музу.'
        },
        {
            'telegram_id': 2003,
            'full_name': 'Игорь',
            'age': 20,
            'gender': 'Парень',
            'city': 'Москва',
            'bio': 'Студент МГТУ. Люблю робототехнику и шахматы.'
        }
    ]

    async with async_session() as session:
        for user_data in test_users:
            try:
                # Создаем пользователя
                user = await create_user(session, user_data)
                # Искусственно накрутим немного лайков некоторым для теста рейтинга
                if user.full_name in ['Мария', 'Александр']:
                    user.likes_received = 10
                    user.dislikes_received = 2
                
                await session.commit()
                # Пересчитываем им рейтинг сразу
                await recalculate_user_rating(session, user.telegram_id)
                print(f"✅ Добавлен(а) {user.full_name}")
            except Exception as e:
                print(f"⚠️ Ошибка при добавлении {user_data['full_name']}: {e}")
                await session.rollback()

    print("\n✨ База готова к демонстрации!")

if __name__ == "__main__":
    asyncio.run(seed_data())