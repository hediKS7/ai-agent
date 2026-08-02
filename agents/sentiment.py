"""
Shared sentiment/emotion handling layer.

Emotion detection itself now lives in ``agents.nlp.sentiment.analyze_sentiment``
(rule-based, no LLM). This module handles the stateful side:
persisting emotional state, computing weekly/sustained patterns, building the
prompt-injected sentiment context, and enforcing response length.
"""
from backend.core.database import AsyncSessionLocal
from sqlalchemy import text


async def save_emotional_state(user_id: str, emotion: str, intensity: float, note: str):
    """Track emotional state over time per user."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("""
                INSERT INTO emotional_history (user_id, emotion, intensity, note, created_at)
                VALUES (:user_id, :emotion, :intensity, :note, NOW())
            """), {"user_id": user_id, "emotion": emotion,
                   "intensity": intensity, "note": note})
            await db.commit()
    except Exception as e:
        print(f"[sentiment] Save failed: {e}")

async def get_emotional_pattern(user_id: str, days: int = 7) -> dict:
    """Get emotional pattern over the last N days."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT emotion, AVG(intensity) as avg_intensity, COUNT(*) as count
                FROM emotional_history
                WHERE user_id = :user_id
                AND created_at > NOW() - make_interval(days => :days)
                GROUP BY emotion
                ORDER BY count DESC
                LIMIT 5
            """), {"user_id": user_id, "days": days})
            rows = result.fetchall()
            if not rows:
                return {}
            dominant = rows[0]
            return {
                "dominant_emotion": dominant[0],
                "avg_intensity": float(dominant[1]),
                "pattern": [{"emotion": r[0], "count": r[2]} for r in rows]
            }
    except Exception as e:
        print(f"[sentiment] Pattern fetch failed: {e}")
        return {}

async def get_sustained_pattern(user_id: str, lookback: int = 5) -> dict:
    """Check if the user has been in a sustained negative state (3+ consecutive)."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT emotion FROM emotional_history
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :lookback
            """), {"user_id": user_id, "lookback": lookback})
            rows = result.fetchall()
        if len(rows) < 3:
            return {"active": False, "emotions": [], "count": 0}
        recent = [r[0] for r in rows]
        distress_signals = {"stressed", "anxious", "burned_out", "frustrated", "sad"}
        sustained = [e for e in recent if e in distress_signals]
        count = 0
        max_run = 0
        for e in recent:
            if e in distress_signals:
                count += 1
                max_run = max(max_run, count)
            else:
                count = 0
        active = max_run >= 3
        return {
            "active": active,
            "emotions": recent,
            "count": max_run,
            "dominant": sustained[0] if sustained else "neutral"
        }
    except Exception as e:
        print(f"[sentiment] Sustained pattern check failed: {e}")
        return {"active": False, "emotions": [], "count": 0}


def enforce_response_length(text: str, max_sentences: int) -> str:
    """Truncate to max_sentences if longer. Works for plain text."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= max_sentences:
        return text
    return " ".join(sentences[:max_sentences])


def build_sentiment_context(sentiment: dict, pattern: dict, sustained: dict = None) -> str:
    """Format sentiment data for injection into prompts."""
    lines = []
    emotion = sentiment.get("emotion", "neutral")
    intensity = sentiment.get("intensity", 0.5)
    pacing = sentiment.get("pacing_needed", "normal")
    length = sentiment.get("response_length", "medium")
    note = sentiment.get("note", "")

    lines.append(f"Current emotional state: {emotion} (intensity {intensity:.1f}/1.0)")
    lines.append(f"Pacing needed: {pacing}")
    lines.append(f"Response length: {length}")
    if note:
        lines.append(f"What they need right now: {note}")

    if pattern.get("dominant_emotion"):
        dom = pattern["dominant_emotion"]
        avg = pattern.get("avg_intensity", 0)
        lines.append(f"Pattern this week: mostly {dom} (avg intensity {avg:.1f})")
        if dom in ["stressed", "burned_out", "anxious"] and avg > 0.6:
            lines.append("Alert: user has been consistently under pressure — reduce friction, be gentler than usual")

    if sustained and sustained.get("active"):
        lines.append(f"SUSTAINED DISTRESS: {sustained['count']} consecutive {sustained['dominant']} signals — prioritize grounding over tasks")

    return "\n".join(lines)
