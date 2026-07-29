import json
from backend.core.config import settings

if settings.redis_url:
    import redis.asyncio as redis
    pool = redis.from_url(settings.redis_url, decode_responses=True)
else:
    pool = None

async def save_short_term(conversation_id: str, messages: list, ttl: int = 3600):
    if pool is None:
        return
    await pool.setex(f"chat:{conversation_id}", ttl, json.dumps(messages))

async def get_short_term(conversation_id: str) -> list:
    if pool is None:
        return []
    data = await pool.get(f"chat:{conversation_id}")
    return json.loads(data) if data else []
