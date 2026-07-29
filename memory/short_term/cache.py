import redis.asyncio as redis
import json
from backend.core.config import settings

pool = redis.from_url(settings.redis_url, decode_responses=True)

async def save_short_term(conversation_id: str, messages: list, ttl: int = 3600):
    await pool.setex(f"chat:{conversation_id}", ttl, json.dumps(messages))

async def get_short_term(conversation_id: str) -> list:
    data = await pool.get(f"chat:{conversation_id}")
    return json.loads(data) if data else []