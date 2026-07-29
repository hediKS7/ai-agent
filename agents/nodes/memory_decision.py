from agents.llm import get_llm
from agents.state import AgentState
import json

DECISION_PROMPT = """You are a memory manager for an AI assistant. Decide how memory should evolve.

Existing memories (use the NUMBER as memory_id in your response):
{existing_memories}

New observation: "{new_observation}"
Agent response: "{agent_response}"

Return ONLY valid JSON:
{{
  "profile_updates": {{}},
  "semantic_actions": [
    {{
      "action": "insert|update|merge|delete|archive|ignore",
      "memory_id": null,
      "content": "fact to store",
      "importance": 0.8,
      "reason": "why"
    }}
  ],
  "episodic_actions": [
    {{
      "action": "insert|ignore",
      "content": "what happened",
      "importance": 0.7
    }}
  ]
}}

Rules:
- INSERT: new fact (memory_id = null)
- UPDATE: fix existing (use NUMBER as memory_id)
- DELETE/ARCHIVE: fact is false/outdated (use NUMBER)
- IGNORE: trivial or already known

Importance: 0.9+=explicit personal facts, 0.7-0.9=preferences, below 0.5=ignore
Return ONLY the JSON, no explanation."""

async def memory_decision_node(state: AgentState) -> AgentState:
    user_message = state["messages"][-1].content.strip()
    agent_response = state.get("final_response", "").strip()
    candidates = state.get("candidate_memories", [])

    skip = ["hi", "hello", "ok", "thanks", "sure", "yes", "no", "bye"]
    if len(user_message) < 10 or user_message.lower().strip() in skip:
        return {**state, "memory_actions": None}

    id_map = {}
    if candidates:
        lines = []
        for i, c in enumerate(candidates):
            num = str(i + 1)
            id_map[num] = c.get("id")
            lines.append(f"{num}. {c['content']} (similarity: {c.get('cosine', 0):.2f})")
        existing = "\n".join(lines)
    else:
        existing = "No existing memories."

    try:
        llm = get_llm()
        result = await llm.ainvoke(DECISION_PROMPT.format(
            existing_memories=existing,
            new_observation=user_message[:300],
            agent_response=agent_response[:200]
        ))
        text = result.content.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            return {**state, "memory_actions": None}

        actions = json.loads(text[start:end])

        for sa in actions.get("semantic_actions", []):
            mid = sa.get("memory_id")
            if mid is not None:
                real_uuid = id_map.get(str(mid))
                if real_uuid:
                    sa["memory_id"] = real_uuid
                else:
                    print(f"[memory_decision] No UUID for index {mid}, converting to insert")
                    sa["action"] = "insert"
                    sa["memory_id"] = None

        print(f"[memory_decision] Actions: {len(actions.get('semantic_actions', []))} semantic, {len(actions.get('episodic_actions', []))} episodic")
        return {**state, "memory_actions": actions}

    except Exception as e:
        print(f"[memory_decision] Failed: {e}")
        return {**state, "memory_actions": None}
