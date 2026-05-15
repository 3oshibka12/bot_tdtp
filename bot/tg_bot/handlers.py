from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from redis.asyncio import Redis
from tg_bot.keyboards import get_gender_kb, get_menu_kb, get_profile_actions_kb, get_empty_feed_kb

from db.database import async_session
import services.crud
import services.cache

import io
from services.s3_service import upload_photo_to_s3, get_photo_from_s3

# Создаем роутер
router = Router()

# FSM для регистрации
class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    bio = State()
    photo = State()

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    """Обработка команды /start"""
    args = message.text.split()
    if len(args) > 1:
        referrer_id = int(args[1])
        if referrer_id != message.from_user.id:
            async with async_session() as session:
                referrer = await services.crud.get_user(session, referrer_id)
                if referrer:
                    referrer.referrals_count += 1
                    await session.commit()
    
    await state.clear()
    async with async_session() as session:
        user = await services.crud.get_user(session, message.from_user.id)
    
    if user:
        await message.answer(
            f"С возвращением, {user.full_name}! 👋", 
            reply_markup=get_menu_kb()
        )
    else:
        await message.answer(
            "Привет! Давай создадим анкету для знакомств.\n\n<b>Как тебя зовут?</b>"
        )
        await state.set_state(RegState.name)

@router.callback_query(F.data == "main_menu")
async def back_to_menu(call: CallbackQuery):
    """Возврат в главное меню"""
    await call.answer()
    await call.message.edit_text("Главное меню:", reply_markup=get_menu_kb())

# --- Регистрация ---

@router.message(RegState.name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени"""
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegState.age)

@router.message(RegState.age)
async def process_age(message: Message, state: FSMContext):
    """Обработка возраста"""
    if not message.text.isdigit():
        await message.answer("❌ Введи возраст числом!")
        return
    
    age = int(message.text)
    if not (18 <= age <= 100):
        await message.answer("❌ Возраст должен быть от 18 до 100!")
        return
    
    await state.update_data(age=age)
    await message.answer("Укажи пол:", reply_markup=get_gender_kb())
    await state.set_state(RegState.gender)

@router.callback_query(RegState.gender, F.data.startswith("gender_"))
async def process_gender(call: CallbackQuery, state: FSMContext):
    """Обработка выбора пола"""
    gender = "Парень" if call.data == "gender_male" else "Девушка"
    await state.update_data(gender=gender)
    await call.answer()
    await call.message.edit_text(f"✅ Пол: {gender}")
    await call.message.answer("Из какого города?")
    await state.set_state(RegState.city)

@router.message(RegState.city)
async def process_city(message: Message, state: FSMContext):
    """Обработка города"""
    await state.update_data(city=message.text)
    await message.answer("Расскажи о себе (интересы, хобби, кого ищешь):")
    await state.set_state(RegState.bio)

@router.message(RegState.bio)
async def process_bio(message: Message, state: FSMContext):
    """Шаг ввода 'О себе' -> Переход к фото"""
    # Сохраняем bio в память состояний (state), а не сразу в базу
    await state.update_data(bio=message.text)
    
    # Просим отправить фотографию
    await message.answer("📸 Отлично! Теперь отправь свое фото для профиля:")
    await state.set_state(RegState.photo)


@router.message(RegState.photo, F.photo)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    """Завершение регистрации: Загрузка фото в S3 и сохранение в БД"""
    await message.answer("⏳ Загружаю фото в базу данных, подожди секунду...")
    
    # 1. Скачиваем фото из Телеграма
    photo_file = await bot.get_file(message.photo[-1].file_id)
    downloaded_file = io.BytesIO()
    await bot.download_file(photo_file.file_path, downloaded_file)
    
    # 2. Грузим фото в наш S3 (Minio)
    s3_url = upload_photo_to_s3(downloaded_file)
    print(f"✅ ФОТО УСПЕШНО ЗАГРУЖЕНО В S3: {s3_url}")
    
    # 3. Достаем все данные пользователя из памяти
    data = await state.get_data()
    reg_data = {
        'telegram_id': message.from_user.id,
        'full_name': data['name'],
        'age': data['age'],
        'gender': data['gender'],
        'city': data['city'],
        'bio': data['bio'],
        'photo_url': s3_url,
        'photo_count': 1
    }
    
    # 4. Сохраняем всё в базу данных
   
    async with async_session() as session:
        await services.crud.create_user(session, reg_data)
    
    # 5. Радуем юзера
    await message.answer(
        "🎉 Анкета создана и фото загружено в надежное хранилище S3!", 
        reply_markup=get_menu_kb()
    )
    await state.clear()

# --- Просмотр своей анкеты ---

@router.callback_query(F.data == "my_profile")
async def show_profile(call: CallbackQuery):
    """Показ своей анкеты"""
    async with async_session() as session:
        user = await services.crud.get_user(session, call.from_user.id)
    
    if not user:
        await call.answer("Анкета не найдена", show_alert=True)
        return
    
    text = (
        f"👤 <b>Твоя анкета</b>\n\n"
        f"{user.full_name}, {user.age}\n"
        f"📍 {user.city}\n\n"
        f"💬 <b>О себе:</b> {user.bio}\n\n"
        f"📊 <b>Рейтинг:</b> {user.rating:.1f}/10\n"
        f"📸 Фото: {user.photo_count}\n"
        f"❤️ Лайков: {user.likes_received} | 💔 Дизлайков: {user.dislikes_received}\n"
        f"🔥 Мэтчей: {user.match_count}"
    )
    await call.answer()
    if getattr(user, 'photo_url', None):
        photo_bytes = get_photo_from_s3(user.photo_url)
        if photo_bytes:
            # Удаляем старое текстовое сообщение
            try: await call.message.delete() 
            except: pass
            
            # Отправляем новое сообщение с ФОТО и текстом
            await call.message.answer_photo(
                photo=BufferedInputFile(photo_bytes, filename="avatar.jpg"),
                caption=text,
                reply_markup=get_menu_kb()
            )
            return

    # Если фотки нет, просто меняем текст
    try:
        await call.message.edit_text(text, reply_markup=get_menu_kb())
    except Exception:
        pass

# --- Поиск анкет ---

@router.callback_query(F.data == "search_profiles")
async def start_search(call: CallbackQuery, redis: Redis, bot: Bot):
    """Начало поиска анкет"""
    await call.answer()
    await show_next_profile(call.message, redis, bot)

async def show_next_profile(message: Message, redis: Redis, bot: Bot):
    user_id = message.chat.id
    
    # 1. Пытаемся взять из Redis
    next_id = await services.cache.get_next_profile_id(redis, user_id)
    
    # 2. Если в Redis пусто — идем в БД за пачкой (10 штук)
    if not next_id:
        async with async_session() as session:
            me = await services.crud.get_user(session, user_id)
            if not me: return
            
            profiles = await services.crud.get_profiles_for_viewing(session, me, limit=10)
            if not profiles:
                await message.answer("😔 Анкеты закончились! Загляни позже.", reply_markup=get_empty_feed_kb())
                return
            
            p_ids = [p.telegram_id for p in profiles]
            # Первую показываем сразу
            next_id = p_ids[0]
            # Остальные 9 — в кэш
            if len(p_ids) > 1:
                await services.cache.fill_user_feed(redis, user_id, p_ids[1:])

    # 3. Отображение (берем данные из БД по next_id)
    async with async_session() as session:
        profile = await services.crud.get_user(session, next_id)
        if not profile: return # На случай удаления

        text = (
            f"👤 <b>{profile.full_name}</b>, {profile.age}\n"
            f"📍 {profile.city}\n"
            f"⭐️ Рейтинг: {profile.rating}\n\n"
            f"💬 {profile.bio}"
        )
        
        try: await message.delete() 
        except: pass
        
        # Если у анкеты есть фото в S3 — показываем его
        if getattr(profile, 'photo_url', None):
            photo_bytes = get_photo_from_s3(profile.photo_url)
            if photo_bytes:
                await message.answer_photo(
                    photo=BufferedInputFile(photo_bytes, filename="photo.jpg"),
                    caption=text,
                    reply_markup=get_profile_actions_kb(profile.telegram_id)
                )
                return
        
        # Если фото нет — выводим просто текст
        await message.answer(text, reply_markup=get_profile_actions_kb(profile.telegram_id))
# --- Обработка свайпов ---

@router.callback_query(F.data.startswith(("like_", "dislike_")))
async def handle_swipe(call: CallbackQuery, redis: Redis, bot: Bot):
    """Обработка лайка/дизлайка"""
    action, target_id_str = call.data.split("_")
    target_id = int(target_id_str)
    initiator_id = call.from_user.id
    
    async with async_session() as session:
        is_match = await services.crud.record_interaction(session, initiator_id, target_id, action)
        
        if is_match:
            target = await services.crud.get_user(session, target_id)
            initiator = await services.crud.get_user(session, initiator_id)
            
            await call.answer("🎉 Это мэтч!", show_alert=True)
            
            # 1. Отправляем сообщение ТОМУ, КОГО ЛАЙКНУЛИ (Target)
            try:
                await bot.send_message(
                    target_id, 
                    f"💖 <b>МЭТЧ!</b> У вас взаимная симпатия с {initiator.full_name}!\n"
                    f"Напиши первым: <a href='tg://user?id={initiator.telegram_id}'>Перейти в профиль</a>"
                )
            except Exception:
                pass 
                
            # 2. Отправляем сообщение ТЕБЕ (Initiator)
            try:
                await bot.send_message(
                    initiator_id, 
                    f"💖 <b>МЭТЧ!</b> У вас взаимная симпатия с {target.full_name}!\n"
                    f"Скорее пиши: <a href='tg://user?id={target.telegram_id}'>Перейти в профиль</a>"
                )
            except Exception:
                pass
    
    await call.answer()
    await show_next_profile(call.message, redis, bot)

@router.callback_query(F.data == "invite_friend")
async def invite_friend_callback(call: CallbackQuery, bot: Bot):
    """Обработка кнопки 'Пригласить друга'"""
    # Получаем инфу о боте, чтобы динамически вставить его юзернейм
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={call.from_user.id}"
    
    text = (
        f"🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"🎁 Отправь её друзьям! За каждого друга, который создаст анкету по твоей ссылке, "
        f"твой итоговый рейтинг (Уровень 3) вырастет на 1.0 балл!"
    )
    
    # Обязательно "отвечаем" на коллбэк, чтобы кнопка перестала мигать часиками
    await call.answer()
    
    # Отправляем сообщение
    await call.message.answer(text)

@router.callback_query(F.data == "my_matches")
async def show_matches(call: CallbackQuery):   
    async with async_session() as session:
        matches = await services.crud.get_user_matches(session, call.from_user.id)
    
    if not matches:
        await call.answer("У тебя пока нет мэтчей 😔\nБольше лайкай!", show_alert=True)
        return
        
    text = "🔥 <b>Твои мэтчи:</b>\n\n"
    for i, m in enumerate(matches, 1):
        # Делаем кликабельное имя, которое ведет в ЛС
        text += f"{i}. {m.full_name} — <a href='tg://user?id={m.telegram_id}'>Написать</a>\n"
        
    await call.answer()
    
    # Удаляем старое сообщение с фоткой (если было)
    try: await call.message.delete()
    except: pass
    
    await call.message.answer(text, reply_markup=get_menu_kb())


@router.callback_query(F.data == "reset_feed")
async def reset_feed_call(call: CallbackQuery, redis: Redis, bot: Bot):   
    async with async_session() as session:
        await services.crud.reset_interactions(session, call.from_user.id)
    
    # Обязательно очищаем кэш ленты в Редисе, чтобы пошел новый запрос в БД
    await redis.delete(f"feed:{call.from_user.id}")
    
    await call.answer("🔄 Лента сброшена! Ищем анкеты...", show_alert=False)
    
    # Удаляем старое сообщение
    try: await call.message.delete()
    except: pass
    
    # Запускаем поиск заново
    await show_next_profile(call.message, redis, bot)