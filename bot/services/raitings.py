from sqlalchemy.ext.asyncio import AsyncSession
from services.crud import get_user
from sqlalchemy import select, and_, func
from db.database import User, Interaction

async def recalculate_user_rating(session: AsyncSession, user_id: int):
    user = await get_user(session, user_id)
    if not user:
        return
    
    # Уровень 1: Полнота (30% веса)
    l1_score = (user.profile_completeness / 100) * 10
    
    # Уровень 2: Поведение (60% веса)
    total_views = user.likes_received + user.dislikes_received
    if total_views > 0:
        l2_score = (user.likes_received / total_views) * 10
    else:
        l2_score = 5.0 # Средний для новичков
    
    # Бонус за мэтчи
    match_bonus = min(user.match_count * 0.5, 3.0)
    l2_score = min(l2_score + match_bonus, 10.0)

    # Рефферальный бонусс!!
    referral_bonus = min(user.referrals_count * 1.0, 5.0)

    # Уровень 3: Итоговый (Комбинированный)
    final_rating = (l1_score * 0.3) + (l2_score * 0.6) + (5.0 * 0.1) + referral_bonus
    
    user.rating = round(min(final_rating, 10.0), 2)
    await session.commit()

async def recalculate_all_ratings(session: AsyncSession):
    result = await session.execute(select(User.telegram_id))
    user_ids = [row[0] for row in result.fetchall()]
    for uid in user_ids:
        await recalculate_user_rating(session, uid)
