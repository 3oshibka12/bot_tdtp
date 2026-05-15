from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import User, Interaction

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
    from services.raitings import recalculate_user_rating

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


async def get_user_matches(session: AsyncSession, user_id: int) -> list[User]:
    """Получает список пользователей, с которыми у нас взаимный лайк"""
    # 1. Кого лайкнул я?
    my_likes_query = select(Interaction.target_id).where(
        and_(Interaction.initiator_id == user_id, Interaction.action == 'like')
    )
    my_likes = (await session.execute(my_likes_query)).scalars().all()
    if not my_likes: return []
    
    # 2. Кто из них лайкнул меня?
    mutual_likes_query = select(Interaction.initiator_id).where(
        and_(
            Interaction.target_id == user_id, 
            Interaction.initiator_id.in_(my_likes),
            Interaction.action == 'like'
        )
    )
    mutual_likes = (await session.execute(mutual_likes_query)).scalars().all()
    if not mutual_likes: return []
    
    # 3. Достаем их профили
    users_query = select(User).where(User.telegram_id.in_(mutual_likes))
    res = await session.execute(users_query)
    return list(res.scalars().all())

async def reset_interactions(session: AsyncSession, user_id: int):
    """Удаляет историю просмотров, чтобы начать ленту сначала"""
    stmt = delete(Interaction).where(Interaction.initiator_id == user_id)
    await session.execute(stmt)
    await session.commit()