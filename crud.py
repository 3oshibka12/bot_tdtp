from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import User, Interaction

# --- CRUD для анкет ---

async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, data: dict) -> User:
    # Вычисляем первичный рейтинг сразу
    new_user = User(**data)
    # Считаем полноту анкеты (Уровень 1)
    score = 0
    if data.get('full_name'): score += 1
    if data.get('age'): score += 1
    if data.get('city'): score += 1
    if data.get('bio') and len(data.get('bio')) > 10: score += 2
    new_user.profile_completeness = (score / 5) * 100
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

# --- Логика рейтингов (Уровни 1, 2, 3) ---

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
    
    # Уровень 3: Итоговый (Комбинированный)
    final_rating = (l1_score * 0.3) + (l2_score * 0.6) + (5.0 * 0.1)
    
    user.rating = round(final_rating, 2)
    await session.commit()

async def recalculate_all_ratings(session: AsyncSession):
    result = await session.execute(select(User.telegram_id))
    user_ids = [row[0] for row in result.fetchall()]
    for uid in user_ids:
        await recalculate_user_rating(session, uid)

# --- Ранжирование для ленты ---

async def get_profiles_for_viewing(session: AsyncSession, user: User, limit: int = 10) -> list[User]:
    # Кого уже видели
    v_query = select(Interaction.target_id).where(Interaction.initiator_id == user.telegram_id)
    v_res = await session.execute(v_query)
    viewed_ids = [r[0] for r in v_res.fetchall()]
    viewed_ids.append(user.telegram_id)

    opp_gender = "Девушка" if user.gender == "Парень" else "Парень"
    
    stmt = (
        select(User)
        .where(and_(User.telegram_id.notin_(viewed_ids), User.gender == opp_gender))
        .order_by((User.city != user.city), User.rating.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())

# --- Взаимодействия ---

async def record_interaction(session: AsyncSession, initiator_id: int, target_id: int, action: str):
    interaction = Interaction(initiator_id=initiator_id, target_id=target_id, action=action)
    session.add(interaction)
    
    target = await get_user(session, target_id)
    if target:
        if action == 'like': target.likes_received += 1
        else: target.dislikes_received += 1
    
    is_match = False
    if action == 'like':
        m_query = select(Interaction).where(and_(
            Interaction.initiator_id == target_id,
            Interaction.target_id == initiator_id,
            Interaction.action == 'like'
        ))
        m_res = await session.execute(m_query)
        if m_res.scalar_one_or_none():
            is_match = True
            init_user = await get_user(session, initiator_id)
            if init_user: init_user.match_count += 1
            if target: target.match_count += 1
            
    await session.commit()
    # Сразу обновляем рейтинг цели
    await recalculate_user_rating(session, target_id)
    return is_match