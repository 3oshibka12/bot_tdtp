from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
        [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data="search_profiles")],
        [InlineKeyboardButton(text="🔗 Пригласить друга", callback_data="invite_friend")]
    ])

def get_profile_actions_kb(target_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{target_id}"),
            InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{target_id}")
        ],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")]
    ])