import json
import time

import redis.asyncio as aioredis


TTL_SECONDS = 7 * 24 * 3600  # 7 days


async def cache_record(
    r: aioredis, key: str, data: dict, ttl: int = TTL_SECONDS
) -> None:
    try:
        await r.set(key, json.dumps(data, default=str), ex=ttl)
    except Exception:
        pass


async def get_cached(r: aioredis, key: str) -> dict | None:
    try:
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def update_recent_set(r: aioredis, set_key: str, member_id: str) -> None:
    try:
        await r.zadd(set_key, {member_id: time.time()})
        await r.zremrangebyrank(set_key, 0, -101)
    except Exception:
        pass


async def delete_cached(r: aioredis, *keys: str) -> None:
    """
    T008: 批量删除缓存键

    Args:
        r: Redis 客户端
        *keys: 要删除的缓存键列表

    Note:
        Redis 异常不抛出,保持现有容错风格
    """
    if not keys:
        return

    try:
        await r.delete(*keys)
    except Exception:
        pass


def serialize_topic_row(row: dict) -> dict:
    """
    T009: 序列化 topic 行用于缓存

    Args:
        row: topic 完整行字典

    Returns:
        序列化后的字典,id/created_at/updated_at 转为字符串
    """
    return {
        k: str(v)
        if v is not None and k in ("id", "revisit_of", "created_at", "updated_at")
        else v
        for k, v in row.items()
    }
