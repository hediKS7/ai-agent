from agents.llm import get_llm
from backend.core.database import AsyncSessionLocal
from sqlalchemy import text
from memory.vector.store import upsert_by_category, reset_chat_count

SUMMARIZER_PROMPT = """You are a memory consolidation agent. Read the user's recent chat history and extract durable facts.

Recent conversations:
{chat_history}

Extract the most important facts about this user using these exact prefixes:
- Location: [city, country] — only if mentioned explicitly and recently
- Name: [name]
- Education: [details]
- Goal: [details]
- Job: [details]
- Interest: [details]
- Language: [details]

IMPORTANT: Only extract facts that appear MULTIPLE TIMES or are very recent. Do not overwrite recent updates with older information.
If none worth saving, respond: NONE"""

async def summarizer_agent(user_id: str) -> str:
    print(f"[Summarizer] Running consolidation for user {user_id}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT content, created_at FROM episodic_memories
            WHERE user_id = :user_id
            ORDER BY created_at DESC LIMIT 20
        """), {"user_id": user_id})
        rows = result.fetchall()

    if not rows:
        await reset_chat_count(user_id, "No memories to consolidate.")
        return "No memories to consolidate."

    chat_history = "\n".join([f"[{r[1]}] {r[0][:200]}" for r in rows])
    llm = get_llm()
    response = await llm.ainvoke(SUMMARIZER_PROMPT.format(chat_history=chat_history))
    summary = response.content.strip()

    if summary.upper() != "NONE":
        facts = [
            line.strip().lstrip("- ").strip()
            for line in summary.split("\n")
            if line.strip().startswith("-") and len(line.strip()) > 15
        ]
        # Skip Location facts in summarizer — user-stated facts take priority
        for fact in facts:
            if not fact.startswith("Location:"):
                await upsert_by_category(user_id, fact, category="consolidated")
            else:
                print(f"[Summarizer] Skipping Location fact (user-stated takes priority): {fact[:50]}")

    await reset_chat_count(user_id, summary)
    print(f"[Summarizer] Done")
    return summary
