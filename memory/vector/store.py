from backend.core.database import AsyncSessionLocal
from sqlalchemy import text
from langchain_mistralai import MistralAIEmbeddings
from backend.core.config import settings
import uuid as uuid_lib
import math
from datetime import datetime, timezone

embeddings_client = MistralAIEmbeddings(
    model="mistral-embed",
    api_key=settings.mistral_api_key,
    timeout=30,
    max_retries=3
)

async def embed(text_input: str) -> list[float]:
    for attempt in range(3):
        try:
            return await embeddings_client.aembed_query(text_input)
        except Exception as e:
            if attempt == 2:
                raise
            import asyncio
            await asyncio.sleep(2 ** attempt)

# ── RECENCY SCORING ───────────────────────────────────────────────────────────

def recency_score(created_at, lambda_decay: float = 0.01) -> float:
    """exp(-λ × days). Decays to 74% after 30 days, 37% after 100 days."""
    if not created_at:
        return 1.0
    if hasattr(created_at, 'tzinfo') and created_at.tzinfo:
        now = datetime.now(timezone.utc)
    else:
        now = datetime.utcnow()
        created_at = created_at.replace(tzinfo=None) if hasattr(created_at, 'tzinfo') else created_at
    days = max(0, (now - created_at).days)
    return math.exp(-lambda_decay * days)

# ── PROFILE LAYER (Layer 1) ───────────────────────────────────────────────────

async def get_user_profile(user_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT profile FROM user_profiles WHERE user_id = :user_id
        """), {"user_id": user_id})
        row = result.fetchone()
        if row and row[0]:
            import json
            profile = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            return profile
        return {}

async def update_user_profile(user_id: str, updates: dict):
    """Merge new facts into JSONB profile. Lists are appended (no duplicates)."""
    import json
    existing = await get_user_profile(user_id)
    for key, value in updates.items():
        if not value:
            continue
        if isinstance(value, list):
            existing_list = existing.get(key, [])
            for item in value:
                if item and item not in existing_list:
                    existing_list.append(item)
            existing[key] = existing_list
        else:
            existing[key] = value

    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO user_profiles (user_id, profile, updated_at)
            VALUES (:user_id, cast(:profile as jsonb), NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET profile = cast(:profile as jsonb), updated_at = NOW()
        """), {"user_id": user_id, "profile": json.dumps(existing, ensure_ascii=False)})
        await db.commit()
    print(f"[profile] Updated: {list(updates.keys())}")

# ── EPISODIC MEMORY (Layer 2) ─────────────────────────────────────────────────

async def save_episodic_memory(user_id: str, conversation_id: str, content: str, event_type: str = "chat"):
    embedding = await embed(content)
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO episodic_memories (user_id, content, embedding, event_type)
            VALUES (:user_id, :content, CAST(:embedding AS vector), :event_type)
        """), {"user_id": user_id, "content": content,
               "embedding": str(embedding), "event_type": event_type})
        await db.commit()

async def search_episodic_memory(user_id: str, query: str, limit: int = 3, min_similarity: float = 0.3) -> list[dict]:
    """Hybrid: vector similarity + recency score."""
    embedding = await embed(query)
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT content, created_at,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS cosine
            FROM episodic_memories
            WHERE user_id = :user_id
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 20
        """), {"user_id": user_id, "embedding": str(embedding)})
        rows = result.fetchall()

    candidates = []
    for r in rows:
        cosine = float(r[2])
        rec = recency_score(r[1])
        hybrid = 0.8 * cosine + 0.2 * rec
        if cosine >= min_similarity:
            candidates.append({"content": r[0], "cosine": cosine, "recency": rec, "hybrid": hybrid})

    candidates.sort(key=lambda x: x["hybrid"], reverse=True)
    return candidates[:limit]

# ── SEMANTIC MEMORY (Layer 3) — hybrid scoring ────────────────────────────────

async def search_semantic_memory(user_id: str, query: str, limit: int = 5, min_similarity: float = 0.35) -> list[dict]:
    """
    Hybrid search: 0.8 × cosine + 0.2 × recency.
    Also tries full-text search (tsvector) if available.
    Returns top-5 most relevant active facts.
    """
    embedding = await embed(query)
    async with AsyncSessionLocal() as db:
        # Vector search
        result = await db.execute(text("""
            SELECT content, category, created_at,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS cosine
            FROM semantic_memories
            WHERE user_id = :user_id AND is_active = TRUE
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 20
        """), {"user_id": user_id, "embedding": str(embedding)})
        rows = result.fetchall()

        # Full-text search
        try:
            fts = await db.execute(text("""
                SELECT content, category, created_at, 0.65 AS cosine
                FROM semantic_memories
                WHERE user_id = :user_id AND is_active = TRUE
                AND content_tsv @@ plainto_tsquery('english', :query)
                LIMIT 10
            """), {"user_id": user_id, "query": query})
            fts_rows = fts.fetchall()
        except Exception:
            fts_rows = []

    seen = set()
    candidates = []
    for r in list(rows) + list(fts_rows):
        if r[0] not in seen:
            seen.add(r[0])
            cosine = float(r[3])
            rec = recency_score(r[2])
            hybrid = 0.8 * cosine + 0.2 * rec
            candidates.append({"content": r[0], "category": r[1], "cosine": cosine, "hybrid": hybrid})

    candidates.sort(key=lambda x: x["hybrid"], reverse=True)
    return [c for c in candidates[:limit] if c["cosine"] >= min_similarity]

async def get_all_active_facts(user_id: str) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT content, category FROM semantic_memories
            WHERE user_id = :user_id AND is_active = TRUE
            ORDER BY created_at DESC LIMIT 20
        """), {"user_id": user_id})
        rows = result.fetchall()
        return [{"content": r[0], "category": r[1]} for r in rows]

# ── UNIFIED MEMORY CONTEXT ────────────────────────────────────────────────────

async def build_memory_context(user_id: str, query: str) -> str:
    """
    Build and format the full memory context for injection into prompts.
    Retrieves:
    - Layer 1: User profile (JSONB)
    - Layer 2: Relevant episodic memories (hybrid search)
    - Layer 3: Relevant semantic facts (hybrid search)
    """
    query_lower = query.lower()
    is_about_me = any(w in query_lower for w in [
        "remember", "who am i", "know me", "about me",
        "what do you know", "where do i live", "where i live",
        "my location", "tell me about", "what do you remember",
        "my goal", "my interest", "my name"
    ])

    parts = []

    # Layer 1 — Profile
    try:
        profile = await get_user_profile(user_id)
        if profile:
            parts.append("**Verified profile (always trust this):**")
            for k, v in profile.items():
                if v:
                    parts.append(f"- {k}: {v}")
    except Exception as e:
        print(f"[memory] Profile fetch failed: {e}")

    # Layer 3 — Semantic facts
    try:
        if is_about_me:
            facts = await get_all_active_facts(user_id)
        else:
            facts = await search_semantic_memory(user_id, query, limit=5)

        if facts:
            parts.append("**Known facts about the user:**")
            for f in facts:
                parts.append(f"- {f['content']}")
    except Exception as e:
        print(f"[memory] Semantic search failed: {e}")

    # Layer 2 — Episodic (relevant past exchanges)
    try:
        episodes = await search_episodic_memory(user_id, query, limit=3)
        if episodes:
            parts.append("**Relevant past exchanges:**")
            for e in episodes:
                parts.append(f"- {e['content'][:180]}")
    except Exception as e:
        print(f"[memory] Episodic search failed: {e}")

    result = "\n".join(parts)
    print(f"[memory] Context: {len(parts)} items, is_about_me={is_about_me}")
    return result

# ── WRITE PATH ────────────────────────────────────────────────────────────────

async def upsert_semantic_memory(user_id: str, content: str, category: str = "fact"):
    embedding = await embed(content)
    new_id = str(uuid_lib.uuid4())
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT id, version,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM semantic_memories
            WHERE user_id = :user_id AND is_active = TRUE
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 1
        """), {"user_id": user_id, "embedding": str(embedding)})
        row = result.fetchone()

        if row and float(row[2]) >= 0.82:
            old_id = row[0]
            old_version = row[1]
            await db.execute(text("""
                INSERT INTO semantic_memories
                    (id, user_id, content, embedding, category, version, is_active)
                VALUES (:id, :user_id, :content, CAST(:embedding AS vector),
                        :category, :version, TRUE)
            """), {"id": new_id, "user_id": user_id, "content": content,
                   "embedding": str(embedding), "category": category,
                   "version": old_version + 1})
            await db.execute(text("""
                UPDATE semantic_memories
                SET is_active = FALSE, superseded_by = :new_id, updated_at = NOW()
                WHERE id = :old_id
            """), {"new_id": new_id, "old_id": str(old_id)})
            print(f"[memory] Updated v{old_version}→v{old_version+1}: {content[:50]}")
        else:
            await db.execute(text("""
                INSERT INTO semantic_memories
                    (id, user_id, content, embedding, category, version, is_active)
                VALUES (:id, :user_id, :content, CAST(:embedding AS vector),
                        :category, 1, TRUE)
            """), {"id": new_id, "user_id": user_id, "content": content,
                   "embedding": str(embedding), "category": category})
            print(f"[memory] New fact: {content[:50]}")
        await db.commit()

async def upsert_by_category(user_id: str, content: str, category: str = "fact"):
    prefix = content.split(":")[0].strip() if ":" in content else None
    if prefix and len(prefix) < 30:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT id, version FROM semantic_memories
                WHERE user_id = :user_id AND is_active = TRUE
                AND content LIKE :prefix
                ORDER BY created_at DESC LIMIT 1
            """), {"user_id": user_id, "prefix": f"{prefix}:%"})
            row = result.fetchone()

        if row:
            old_id = row[0]
            old_version = row[1]
            new_id = str(uuid_lib.uuid4())
            embedding = await embed(content)
            async with AsyncSessionLocal() as db:
                await db.execute(text("""
                    INSERT INTO semantic_memories
                        (id, user_id, content, embedding, category, version, is_active)
                    VALUES (:id, :user_id, :content, CAST(:embedding AS vector),
                            :category, :version, TRUE)
                """), {"id": new_id, "user_id": user_id, "content": content,
                       "embedding": str(embedding), "category": category,
                       "version": old_version + 1})
                await db.execute(text("""
                    UPDATE semantic_memories
                    SET is_active = FALSE, superseded_by = :new_id, updated_at = NOW()
                    WHERE id = :old_id
                """), {"new_id": new_id, "old_id": str(old_id)})
                await db.commit()
            print(f"[memory] Category update: {content[:50]}")
            return
    await upsert_semantic_memory(user_id, content, category)

async def increment_chat_count(user_id: str) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT chats_since_last FROM consolidation_log WHERE user_id = :user_id
        """), {"user_id": user_id})
        row = result.fetchone()
        if not row:
            await db.execute(text("""
                INSERT INTO consolidation_log (user_id, chats_since_last)
                VALUES (:user_id, 1)
            """), {"user_id": user_id})
            await db.commit()
            return 1
        count = row[0] + 1
        await db.execute(text("""
            UPDATE consolidation_log SET chats_since_last = :count
            WHERE user_id = :user_id
        """), {"user_id": user_id, "count": count})
        await db.commit()
        return count

async def reset_chat_count(user_id: str, summary: str):
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            UPDATE consolidation_log
            SET chats_since_last = 0, last_consolidated = NOW(), summary = :summary
            WHERE user_id = :user_id
        """), {"user_id": user_id, "summary": summary})
        await db.commit()

# ── MEMORY DECAY + REINFORCEMENT ──────────────────────────────────────────────

async def apply_memory_decay(user_id: str, lambda_decay: float = 0.01):
    """
    Daily decay: importance = importance × e^(-λ × days_since_last_access).
    Run this periodically (e.g., daily via a cron or on each session start).
    """
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            UPDATE semantic_memories
            SET importance_score = GREATEST(
                0.1,
                importance_score * EXP(
                    -:lambda_val * EXTRACT(EPOCH FROM (NOW() - last_accessed)) / 86400
                )
            )
            WHERE user_id = :user_id
            AND is_active = TRUE
            AND last_accessed IS NOT NULL
        """), {"user_id": user_id, "lambda_val": lambda_decay})
        await db.commit()
    print(f"[decay] Applied memory decay for user {user_id}")

async def reinforce_memory(memory_id: str, bonus: float = 0.02):
    """
    When a memory is retrieved and used, reinforce it:
    - Update last_accessed
    - Increment frequency
    - Small importance bonus
    """
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            UPDATE semantic_memories
            SET last_accessed = NOW(),
                frequency = frequency + 1,
                importance_score = LEAST(1.0, importance_score + :bonus)
            WHERE id = :id
        """), {"id": str(memory_id), "bonus": bonus})
        await db.commit()
