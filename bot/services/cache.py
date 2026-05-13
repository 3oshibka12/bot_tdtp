from redis.asyncio import Redis

USER_FEED_KEY = "feed:{user_id}"

async def get_next_profile_id(redis: Redis, user_id: int) -> int | None:
    # Достаем один ID из списка
    pid = await redis.lpop(USER_FEED_KEY.format(user_id=user_id))
    return int(pid) if pid else None

async def fill_user_feed(redis: Redis, user_id: int, profile_ids: list[int]):
    key = USER_FEED_KEY.format(user_id=user_id)
    if profile_ids:
        await redis.rpush(key, *profile_ids)
        # Ставим TTL 30 минут, чтобы кэш не протух
        await redis.expire(key, 1800)