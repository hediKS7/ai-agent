from backend.core.database import AsyncSessionLocal
from sqlalchemy import text
from memory.vector.store import embed, update_user_profile
from agents.state import AgentState
import uuid

async def memory_manager_node(state: AgentState) -> AgentState:
    """
    Deterministic executor — applies memory_decision actions to PostgreSQL.
    No reasoning here, just DB operations.
    """
    actions = state.get("memory_actions")
    user_id = state["user_id"]

    if not actions:
        return state

    semantic_actions = actions.get("semantic_actions", [])
    episodic_actions = actions.get("episodic_actions", [])
    profile_updates = actions.get("profile_updates", {})

    # Execute semantic actions
    for action in semantic_actions:
        op = action.get("action", "ignore").lower()
        content = action.get("content", "").strip()
        memory_id = action.get("memory_id")
        importance = float(action.get("importance", 0.5))

        if not content or op == "ignore":
            continue

        try:
            if op == "insert":
                await _insert_memory(user_id, content, importance)
            elif op == "update" and memory_id:
                await _update_memory(memory_id, content, importance)
            elif op == "merge":
                await _merge_memories(user_id, content, importance, memory_id)
            elif op == "delete" and memory_id:
                await _delete_memory(memory_id)
            elif op == "archive" and memory_id:
                await _archive_memory(memory_id)
            print(f"[memory_manager] {op.upper()}: {content[:50]}")
        except Exception as e:
            print(f"[memory_manager] {op} failed: {e}")

    # Execute episodic actions
    for action in episodic_actions:
        op = action.get("action", "ignore").lower()
        content = action.get("content", "").strip()
        importance = float(action.get("importance", 0.5))
        if not content or op == "ignore" or importance < 0.4:
            continue
        try:
            embedding = await embed(content)
            async with AsyncSessionLocal() as db:
                await db.execute(text("""
                    INSERT INTO episodic_memories
                        (user_id, content, embedding, event_type)
                    VALUES (:user_id, :content, CAST(:embedding AS vector), 'chat')
                """), {"user_id": user_id, "content": content,
                       "embedding": str(embedding)})
                await db.commit()
            print(f"[memory_manager] EPISODIC INSERT: {content[:50]}")
        except Exception as e:
            print(f"[memory_manager] Episodic insert failed: {e}")

    # Update profile
    if profile_updates:
        try:
            await update_user_profile(user_id, profile_updates)
            print(f"[memory_manager] PROFILE UPDATE: {list(profile_updates.keys())}")
        except Exception as e:
            print(f"[memory_manager] Profile update failed: {e}")

    return state


async def _insert_memory(user_id: str, content: str, importance: float):
    embedding = await embed(content)
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO semantic_memories
                (id, user_id, content, embedding, category, version,
                 is_active, importance_score, frequency)
            VALUES (:id, :user_id, :content, CAST(:embedding AS vector),
                    'dynamic', 1, TRUE, :importance, 1)
        """), {"id": str(uuid.uuid4()), "user_id": user_id,
               "content": content, "embedding": str(embedding),
               "importance": importance})
        await db.commit()

async def _update_memory(memory_id: str, new_content: str, importance: float):
    embedding = await embed(new_content)
    async with AsyncSessionLocal() as db:
        # Create new version
        new_id = str(uuid.uuid4())
        # Get old version number
        result = await db.execute(text("""
            SELECT version FROM semantic_memories WHERE id = :id
        """), {"id": str(memory_id)})
        row = result.fetchone()
        old_version = row[0] if row else 1

        await db.execute(text("""
            INSERT INTO semantic_memories
                (id, user_id, content, embedding, category, version,
                 is_active, importance_score, frequency)
            SELECT :new_id, user_id, :content, CAST(:embedding AS vector),
                   category, :version, TRUE, :importance, frequency + 1
            FROM semantic_memories WHERE id = :old_id
        """), {"new_id": new_id, "content": new_content,
               "embedding": str(embedding), "version": old_version + 1,
               "importance": importance, "old_id": str(memory_id)})

        await db.execute(text("""
            UPDATE semantic_memories
            SET is_active = FALSE, superseded_by = :new_id, updated_at = NOW()
            WHERE id = :old_id
        """), {"new_id": new_id, "old_id": str(memory_id)})
        await db.commit()

async def _merge_memories(user_id: str, merged_content: str,
                          importance: float, old_id=None):
    """Archive old memory and insert merged version."""
    if old_id:
        await _archive_memory(old_id)
    await _insert_memory(user_id, merged_content, importance)

async def _delete_memory(memory_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            UPDATE semantic_memories
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = :id
        """), {"id": str(memory_id)})
        await db.commit()

async def _archive_memory(memory_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            UPDATE semantic_memories
            SET is_active = FALSE, archived = TRUE, updated_at = NOW()
            WHERE id = :id
        """), {"id": str(memory_id)})
        await db.commit()
