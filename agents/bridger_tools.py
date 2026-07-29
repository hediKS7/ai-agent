"""
Bridger MVP Tools:
- add_contact: add someone to the relational graph
- find_matches: matchmaking based on field/interests
- draft_introduction: write a warm intro message
- draft_followup: write a follow-up message
- get_network_health: check who needs a follow-up
"""
from langchain_core.tools import tool
from backend.core.database import AsyncSessionLocal
from sqlalchemy import text
from memory.vector.store import embed
import uuid
from datetime import datetime

@tool
async def add_contact(
    name: str,
    role: str = "",
    company: str = "",
    field: str = "",
    how_met: str = "",
    notes: str = "",
    user_id: str = ""
) -> str:
    """Add a person to the user's relational network graph."""
    try:
        content = f"{name} - {role} at {company} - {field} - {notes}"
        embedding = await embed(content)
        contact_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as db:
            await db.execute(text("""
                INSERT INTO network_contacts
                    (id, user_id, name, role, company, field, how_met, notes, embedding)
                VALUES (:id, :user_id, :name, :role, :company, :field, :how_met, :notes, CAST(:emb AS vector))
            """), {
                "id": contact_id, "user_id": user_id,
                "name": name, "role": role, "company": company,
                "field": field, "how_met": how_met, "notes": notes,
                "emb": str(embedding)
            })
            await db.commit()
        # Schedule a follow-up nudge in 14 days
        try:
            from agents.followup import schedule_relationship_checkin
            await schedule_relationship_checkin(
                user_id, name,
                f"Added {name} ({role} at {company}) — follow up naturally",
                days=14
            )
        except Exception:
            pass
        return f"Added {name} ({role} at {company}) to your network."
    except Exception as e:
        return f"Error adding contact: {e}"

@tool
async def find_matches(
    field: str = "",
    interests: str = "",
    user_id: str = ""
) -> str:
    """Find people in the network who match a given field or interest using semantic similarity."""
    try:
        query = f"{field} {interests}".strip()
        embedding = await embed(query)
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT name, role, company, field, notes,
                       1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                FROM network_contacts
                WHERE user_id = :user_id
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT 5
            """), {"emb": str(embedding), "user_id": user_id})
            rows = result.fetchall()

        if not rows:
            return "No matches found in your network yet. Add some contacts first."

        matches = []
        for r in rows:
            if r[5] > 0.3:
                matches.append(f"- {r[0]} ({r[1]} at {r[2]}) — {r[3]}")

        return "Best matches in your network:\n" + "\n".join(matches) if matches else "No strong matches found."
    except Exception as e:
        return f"Error finding matches: {e}"
@tool
async def draft_introduction(
    your_name: str,
    your_context: str,
    target_name: str,
    target_role: str,
    common_ground: str,
    platform: str = "LinkedIn",
    user_id: str = ""
) -> str:
    """
    Draft a warm, specific introduction message.
    NOT a template — personalized based on common ground.
    """
    # Schedule a follow-up to check how the intro went
    if user_id:
        try:
            from agents.followup import schedule_introduction_followup
            await schedule_introduction_followup(
                user_id, target_name,
                f"Drafted intro to {target_name} ({target_role}) via {platform}",
                days=7
            )
        except Exception:
            pass

    return f"""Here's a warm introduction message for {target_name} on {platform}:

---

Hi {target_name},

I came across your work on {common_ground} and it genuinely resonated with me. I'm {your_name} — {your_context}.

I'd love to connect and hear more about your experience with {target_role}. No agenda — just a genuine interest in the work you're doing.

Looking forward to connecting,
{your_name}
---

Feel free to adjust the tone or add a specific detail that caught your attention about their work."""

@tool
async def draft_followup(
    contact_name: str,
    last_interaction: str,
    reason_to_reach_out: str,
    your_name: str
) -> str:
    """
    Draft a natural follow-up message that doesn't feel transactional.
    Based on context of last interaction and a genuine reason to reconnect.
    """
    return f"""Follow-up message for {contact_name}:

---
Hi {contact_name},

{reason_to_reach_out} — thought of you immediately.

Hope things have been going well since {last_interaction}. Would love to catch up if you have 15 minutes sometime.

{your_name}
---

This keeps it light and genuine. Adjust the specific reason to make it feel personal."""

@tool
async def get_network_health(user_id: str) -> str:
    """Check which contacts haven't been reached out to in a while."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT name, role, company, last_contact,
                       relationship_strength
                FROM network_contacts
                WHERE user_id = :user_id
                ORDER BY last_contact ASC NULLS FIRST
                LIMIT 5
            """), {"user_id": user_id})
            rows = result.fetchall()

        if not rows:
            return "No contacts in your network yet."

        output = []
        for r in rows:
            last = r[3].strftime("%B %d") if r[3] else "never"
            output.append(f"- {r[0]} ({r[1]} at {r[2]}) — last contact: {last}")

        return "Contacts that could use a check-in:\n" + "\n".join(output)
    except Exception as e:
        return f"Error checking network: {e}"

def get_bridger_tools():
    return [add_contact, find_matches, draft_introduction, draft_followup, get_network_health]
