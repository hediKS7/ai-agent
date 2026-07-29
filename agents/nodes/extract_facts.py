from memory.vector.store import upsert_by_category, update_user_profile
from agents.state import AgentState
from agents.llm import get_llm
import json

EXTRACT_PROMPT = """Extract personal facts about the user from this exchange.

Use EXACTLY these category prefixes for facts:
- Name: [full name]
- Location: [city, country]
- Education: [school, degree, year]
- Goal: [specific goal]
- Job: [role, company]
- Interest: [topic]
- Language: [language name]
- Project: [project description]
- Skill: [technical skill]

Also extract a JSON profile update (only include keys with clear information found):
Keys: name, location, education, goals (list), interests (list), languages (list), skills (list)

Format EXACTLY as:
FACTS:
- Location: Paris, France
- Goal: Become an AI researcher in Europe

PROFILE_JSON:
{"location": "Paris, France", "goals": ["Become an AI researcher in Europe"]}

If absolutely nothing personal to extract: NONE

User message: {user_message}
Agent response: {agent_response}"""

async def extract_facts_node(state: AgentState) -> AgentState:
    user_message = state["messages"][-1].content.strip()
    agent_response = state.get("final_response", "").strip()
    user_id = state["user_id"]

    # Skip trivial messages
    skip = ["hi", "hello", "ok", "thanks", "sure", "yes", "no",
            "what did", "do you remember", "what do you know"]
    if len(user_message) < 15 or any(s in user_message.lower() for s in skip):
        return state

    if len(agent_response) < 20:
        return state

    try:
        llm = get_llm()
        result = await llm.ainvoke(EXTRACT_PROMPT.format(
            user_message=user_message,
            agent_response=agent_response[:400]
        ))
        text = result.content.strip()

        if text.upper() == "NONE" or not text:
            return state

        # Parse FACTS
        if "FACTS:" in text:
            facts_part = text.split("FACTS:")[1]
            if "PROFILE_JSON:" in facts_part:
                facts_part = facts_part.split("PROFILE_JSON:")[0]
            for line in facts_part.strip().split("\n"):
                fact = line.strip().lstrip("-•* ").strip()
                if len(fact) > 10 and ":" in fact:
                    print(f"[extract_facts] → {fact[:70]}")
                    await upsert_by_category(user_id, fact, category="extracted")

        # Parse PROFILE_JSON
        if "PROFILE_JSON:" in text:
            json_part = text.split("PROFILE_JSON:")[1].strip()
            # Find JSON block
            start = json_part.find("{")
            end = json_part.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    profile_data = json.loads(json_part[start:end])
                    if profile_data:
                        await update_user_profile(user_id, profile_data)
                except json.JSONDecodeError as e:
                    print(f"[extract_facts] JSON parse error: {e}")

    except Exception as e:
        print(f"[extract_facts] Failed: {e}")

    return state
