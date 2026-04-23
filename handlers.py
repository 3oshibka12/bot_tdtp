from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from redis.asyncio import Redis

from database import async_session
import crud
import cache

# Создаем роутер
router = Router()

# FSM для регистрации
class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    bio = State()

# --- Клавиатуры ---

def get_gender_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Парень", callback_data="gender_male"),
            InlineKeyboardButton(text="👩 Девушка", callback_data="gender_female")
        ]
    ])

def get_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Моя анкета", callback_data="my_profile")],
        [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data="search_profiles")]
    ])

def get_profile_actions_kb(target_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{target_id}"),
            InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{target_id}")
        ],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")]
    ])

# --- Хендлеры ---

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    async with async_session() as session:
        user = await crud.get_user(session, message.from_user.id)
    
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
    """Завершение регистрации"""
    data = await state.get_data()
    reg_data = {
        'telegram_id': message.from_user.id,
        'full_name': data['name'],
        'age': data['age'],
        'gender': data['gender'],
        'city': data['city'],
        'bio': message.text
    }
    
    async with async_session() as session:
        await crud.create_user(session, reg_data)
    
    await message.answer(
        "🎉 Анкета создана!\n\n💡 <i>Совет: добавь фото в профиль для повышения рейтинга</i>", 
        reply_markup=get_menu_kb()
    )
    await state.clear()

# --- Просмотр своей анкеты ---

@router.callback_query(F.data == "my_profile")
async def show_profile(call: CallbackQuery):
    """Показ своей анкеты"""
    async with async_session() as session:
        user = await crud.get_user(session, call.from_user.id)
    
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
    await call.message.edit_text(text, reply_markup=get_menu_kb())

# --- Поиск анкет ---

@router.callback_query(F.data == "search_profiles")
async def start_search(call: CallbackQuery, redis: Redis, bot: Bot):
    """Начало поиска анкет"""
    await call.answer()
    await show_next_profile(call.message, redis, bot)

async def show_next_profile(message: Message, redis: Redis, bot: Bot):
    user_id = message.chat.id
    
    # 1. Пытаемся взять из Redis
    next_id = await cache.get_next_profile_id(redis, user_id)
    
    # 2. Если в Redis пусто — идем в БД за пачкой (10 штук)
    if not next_id:
        async with async_session() as session:
            me = await crud.get_user(session, user_id)
            if not me: return
            
            profiles = await crud.get_profiles_for_viewing(session, me, limit=10)
            if not profiles:
                await message.answer("😔 Анкеты закончились! Загляни позже.")
                return
            
            p_ids = [p.telegram_id for p in profiles]
            # Первую показываем сразу
            next_id = p_ids[0]
            # Остальные 9 — в кэш
            if len(p_ids) > 1:
                await cache.fill_user_feed(redis, user_id, p_ids[1:])

    # 3. Отображение (берем данные из БД по next_id)
    async with async_session() as session:
        profile = await crud.get_user(session, next_id)
        if not profile: return # На случай удаления

        text = (
            f"👤 <b>{profile.full_name}</b>, {profile.age}\n"
            f"📍 {profile.city}\n"
            f"⭐️ Рейтинг: {profile.rating}\n\n"
            f"{profile.bio}"
        )
        # Отправляем новую анкету
        await message.answer(text, reply_markup=get_profile_actions_kb(profile.telegram_id))
# --- Обработка свайпов ---

@router.callback_query(F.data.startswith(("like_", "dislike_")))
async def handle_swipe(call: CallbackQuery, redis: Redis, bot: Bot):
    """Обработка лайка/дизлайка"""
    action, target_id_str = call.data.split("_")
    target_id = int(target_id_str)
    initiator_id = call.from_user.id
    
    async with async_session() as session:
        is_match = await crud.record_interaction(session, initiator_id, target_id, action)
        
        if is_match:
            target = await crud.get_user(session, target_id)
            initiator = await crud.get_user(session, initiator_id)
            
            await call.answer("🎉 Это мэтч!", show_alert=True)
            
            # Уведомления обоим пользователям
            try:
                await bot.send_message(
                    target_id, 
                    f"💖 У вас взаимная симпатия с {initiator.full_name}!\n"
                    f"Можете начать общение!"
                )
            except Exception:
                pass  # Если пользователь заблокировал бота
    
    await call.answer()
    await show_next_profile(call.message, redis, bot)