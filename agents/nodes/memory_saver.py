from memory.vector.store import save_episodic_memory, increment_chat_count
from agents.nodes.summarizer import summarizer_agent
from agents.state import AgentState

CONSOLIDATION_THRESHOLD = 10
MIN_LENGTH = 20
SKIP_PATTERNS = [
    "do you remember", "remember me", "who am i",
    "what did i", "give me", "show me", "tell me",
    "what do you know", "where do i live"
]

async def memory_saver_node(state: AgentState) -> AgentState:
    user_message = state["messages"][-1].content.strip()
    agent_response = state.get("final_response", "").strip()
    user_id = state["user_id"]
    conversation_id = state.get("conversation_id") or user_id

    msg_lower = user_message.lower()
    is_trivial = (
        len(user_message) < MIN_LENGTH or
        any(p in msg_lower for p in SKIP_PATTERNS)
    )

    # Save to episodic memory
    if not is_trivial and len(agent_response) > 20:
        exchange = f"User: {user_message}\nAgent: {agent_response[:200]}"
        try:
            await save_episodic_memory(user_id, conversation_id, exchange, "chat")
            print(f"[memory_saver] Episodic saved")
        except Exception as e:
            print(f"[memory_saver] Episodic failed: {e}")

    # Consolidation trigger
    try:
        count = await increment_chat_count(user_id)
        print(f"[memory_saver] Chat count: {count}/{CONSOLIDATION_THRESHOLD}")
        if count >= CONSOLIDATION_THRESHOLD:
            print(f"[memory_saver] Running Summarizer...")
            await summarizer_agent(user_id)
    except Exception as e:
        print(f"[memory_saver] Consolidation failed: {e}")

    return state
