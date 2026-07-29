from backend.core.database import AsyncSessionLocal
from sqlalchemy import text
from memory.vector.store import embed
from agents.state import AgentState

async def retrieve_candidates_node(state: AgentState) -> AgentState:
    """Retrieve top-5 nearest existing memories WITH their real UUIDs."""
    user_message = state["messages"][-1].content
    user_id = state["user_id"]

    try:
        embedding = await embed(user_message)
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT id, content, category,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS cosine
                FROM semantic_memories
                WHERE user_id = :user_id AND is_active = TRUE
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT 5
            """), {"user_id": user_id, "embedding": str(embedding)})
            rows = result.fetchall()
            candidates = [
                {"id": str(r[0]), "content": r[1], "category": r[2], "cosine": float(r[3])}
                for r in rows
            ]
    except Exception as e:
        print(f"[retrieve_candidates] Failed: {e}")
        candidates = []

    print(f"[retrieve_candidates] Found {len(candidates)} candidates")
    return {**state, "candidate_memories": candidates}
