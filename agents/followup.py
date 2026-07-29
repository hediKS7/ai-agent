from backend.core.database import AsyncSessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta
import uuid

# ── Bridger follow-ups ──────────────────────────────────────────────────────

async def schedule_introduction_followup(user_id: str, contact_name: str, context: str, days: int = 7):
    """After an intro is drafted, schedule a nudge to check how it went."""
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO followups (id, user_id, agent_type, followup_type, context, due_at)
            VALUES (:id, :user_id, 'bridger', 'intro_checkin',
                    jsonb_build_object('contact_name', :name, 'context', :context),
                    NOW() + :interval)
        """), {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": contact_name,
            "context": context,
            "interval": timedelta(days=days)
        })
        await db.commit()


async def schedule_relationship_checkin(user_id: str, person_name: str, context: str, days: int = 14):
    """After a silence on a relationship they cared about."""
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO followups (id, user_id, agent_type, followup_type, context, due_at)
            VALUES (:id, :user_id, 'bridger', 'relationship_checkin',
                    jsonb_build_object('person_name', :name, 'context', :context),
                    NOW() + :interval)
        """), {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": person_name,
            "context": context,
            "interval": timedelta(days=days)
        })
        await db.commit()


# ── Inspirer commitment tracking ────────────────────────────────────────────

async def save_commitment(user_id: str, description: str, conversation_id: str, deadline_days: int = 7):
    """Save a commitment the user made for accountability follow-up."""
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO commitments (id, user_id, description, deadline, source_conversation_id)
            VALUES (:id, :user_id, :description, NOW() + :interval, :conv_id)
        """), {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "description": description,
            "interval": timedelta(days=deadline_days),
            "conv_id": conversation_id
        })
        await db.commit()


async def get_overdue_commitments(user_id: str) -> list:
    """Find commitments past deadline that haven't been resolved."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT id, description, deadline, created_at
            FROM commitments
            WHERE user_id = :uid AND status = 'pending' AND deadline < NOW()
            ORDER BY deadline ASC
            LIMIT 3
        """), {"uid": user_id})
        return [{"id": str(r[0]), "description": r[1], "deadline": str(r[2])} for r in result.fetchall()]


async def mark_commitment_resolved(commitment_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "UPDATE commitments SET status = 'resolved' WHERE id = :id"
        ), {"id": commitment_id})
        await db.commit()


# ── Vibber weekly summaries ─────────────────────────────────────────────────

async def needs_weekly_summary(user_id: str) -> bool:
    """Check if 7+ days since last summary and enough emotional data exists."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT COUNT(*) FROM emotional_history
            WHERE user_id = :uid AND created_at > NOW() - INTERVAL '7 days'
        """), {"uid": user_id})
        count = result.scalar()
        if count < 3:
            return False

        result = await db.execute(text("""
            SELECT MAX(created_at) FROM weekly_summaries WHERE user_id = :uid
        """), {"uid": user_id})
        last = result.scalar()
        if last is None:
            return True
        return datetime.utcnow() - last > timedelta(days=7)


async def build_weekly_summary(user_id: str) -> str:
    """Synthesize the week's emotional data into a reflection summary."""
    from agents.llm import get_llm

    async with AsyncSessionLocal() as db:
        entries = await db.execute(text("""
            SELECT emotion, intensity, note, created_at
            FROM emotional_history
            WHERE user_id = :uid AND created_at > NOW() - INTERVAL '7 days'
            ORDER BY created_at DESC
        """), {"uid": user_id})
        rows = entries.fetchall()

    if not rows:
        return ""

    lines = []
    for r in rows[:10]:
        lines.append(f"{r[3].strftime('%a')}: {r[0]} ({r[1]:.1f}) — {r[2] or 'no note'}")
    history = "\n".join(lines)

    prompt = f"""The user's emotional data for this week:

{history}

Write a 2-3 sentence reflection summary. Validate their experience. Note any pattern. Don't give advice.
Keep it warm and grounded. Plain text only."""

    llm = get_llm()
    response = await llm.ainvoke(prompt)
    summary = response.content.strip()

    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO weekly_summaries (id, user_id, summary_text, week_start)
            VALUES (:id, :uid, :text, DATE_TRUNC('week', NOW() - INTERVAL '7 days'))
        """), {
            "id": str(uuid.uuid4()),
            "uid": user_id,
            "text": summary
        })
        await db.commit()

    return summary


# ── General polling ─────────────────────────────────────────────────────────

async def get_due_followups(user_id: str) -> list:
    """Get all untriggered follow-ups that are past due."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT id, agent_type, followup_type, context, due_at
            FROM followups
            WHERE user_id = :uid AND triggered = FALSE AND due_at < NOW()
            ORDER BY due_at ASC
        """), {"uid": user_id})
        return [{
            "id": str(r[0]),
            "agent_type": r[1],
            "followup_type": r[2],
            "context": r[3],
            "due_at": str(r[4])
        } for r in result.fetchall()]


async def mark_followup_triggered(followup_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "UPDATE followups SET triggered = TRUE WHERE id = :id"
        ), {"id": followup_id})
        await db.commit()


async def extract_user_commitment(message: str, user_id: str, conversation_id: str) -> bool:
    """Check if user made a commitment (I'll X by Y pattern) and save it."""
    patterns = [
        r"(?:i['']?ll|i will|let me)\s+(.+?)\s+(?:by|before|this|next|tomorrow|friday|monday|tuesday|wednesday|thursday)",
        r"(?:going to|plan to|will)\s+(.+?)\s+(?:by|before)\s+(.+?)(?:\.|$)",
    ]
    import re
    for pat in patterns:
        match = re.search(pat, message.lower())
        if match:
            # Extract the commitment and estimate deadline
            text = match.group(0)
            await save_commitment(user_id, text, conversation_id, deadline_days=7)
            print(f"[Followup] Saved commitment: {text[:60]}")
            return True
    return False
