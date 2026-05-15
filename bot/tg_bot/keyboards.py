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
        [InlineKeyboardButton(text="🔥 Мои мэтчи", callback_data="my_matches")], # НОВАЯ КНОПКА
        [InlineKeyboardButton(text="🔗 Пригласить друга", callback_data="invite_friend")]
    ])

def get_empty_feed_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="reset_feed")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")]
    ])

def get_profile_actions_kb(target_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{target_id}"),
            InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{target_id}")
        ],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")]
    ])