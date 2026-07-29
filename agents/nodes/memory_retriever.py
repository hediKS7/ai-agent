from memory.vector.store import build_memory_context
from agents.state import AgentState

CONVERSATION_QUERIES = [
    "what did we talk", "what did we discuss", "what have we talked",
    "what was our conversation", "what did you just", "what did i just",
    "remind me what", "recap", "what did we say"
]

async def memory_node(state: AgentState) -> AgentState:
    query = state["messages"][-1].content
    query_lower = query.lower()

    if any(phrase in query_lower for phrase in CONVERSATION_QUERIES):
        print(f"[memory] Conversation recap — no memory injected")
        return {**state, "memory_context": "NO_MEMORY_THIS_IS_CONVERSATION_RECAP"}

    try:
        context = await build_memory_context(state["user_id"], query)
    except Exception as e:
        print(f"[memory_retriever] Warning: {e}")
        context = ""

    return {**state, "memory_context": context}
