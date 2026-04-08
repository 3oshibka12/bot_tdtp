from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from database import async_session, User

router = Router()

class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    bio = State()

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
        [InlineKeyboardButton(text="🔍 Искать пару", callback_data="search")]
    ])


@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    """Реакция на /start"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

    if user:
        await message.answer(f"С возвращением, {user.full_name}! 👋", reply_markup=get_menu_kb())
    else:
        await message.answer("Привет! Давай создадим анкету.\n\nКак тебя зовут?")
        await state.set_state(RegState.name)

@router.message(RegState.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegState.age)

@router.message(RegState.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введи число!")
        return
    
    age = int(message.text)
    if age < 18 or age > 100:
        await message.answer("❌ Возраст должен быть от 18 до 100 лет!")
        return
    
    await state.update_data(age=age)
    await message.answer("Укажи свой пол:", reply_markup=get_gender_kb())
    await state.set_state(RegState.gender)

@router.callback_query(RegState.gender, F.data.startswith("gender_"))
async def process_gender(call: CallbackQuery, state: FSMContext):
    gender = "Парень" if call.data == "gender_male" else "Девушка"
    await state.update_data(gender=gender)
    
    await call.answer()
    await call.message.edit_text(f"✅ Пол: {gender}")
    await call.message.answer("Из какого ты города?")
    await state.set_state(RegState.city)

@router.message(RegState.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Напиши пару слов о себе:")
    await state.set_state(RegState.bio)

@router.message(RegState.bio)
async def process_bio(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Сохраняем в БД
    async with async_session() as session:
        new_user = User(
            telegram_id=message.from_user.id,
            full_name=data['name'],
            age=data['age'],
            gender=data['gender'],
            city=data['city'],
            bio=message.text
        )
        session.add(new_user)
        await session.commit()
    
    await message.answer("🎉 Регистрация завершена!\n\nЧто дальше?", reply_markup=get_menu_kb())
    await state.clear()

@router.callback_query(F.data == "my_profile")
async def show_profile(call: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == call.from_user.id))
        user = result.scalar_one_or_none()

    await call.answer()
    if not user:
        await call.message.answer("Анкета не найдена")
        return
    
    text = (f"👤 {user.full_name}, {user.age}\n"
            f"📍 {user.city}\n\n"
            f"💬 О себе: {user.bio}")
    await call.message.edit_text(text, reply_markup=get_menu_kb())

@router.callback_query(F.data == "search")
async def stub_search(call: CallbackQuery):
    await call.answer("Поиск недоступен", show_alert=True)