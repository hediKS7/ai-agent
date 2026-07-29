from agents.llm import get_llm
from agents.state import AgentState

ROUTER_PROMPT = """Classify the user's message into exactly one category:

- "chat": greetings, small talk, recall questions (e.g. "do you remember me?", "what did I ask earlier?")
- "task": requests requiring planning, research, tools, code analysis, file reading, calculations, or multi-step work

Examples:
- "What did I research earlier?" -> chat
- "Explain this code" -> task
- "Find bugs in my code" -> task
- "Analyze this Python file" -> task
- "Find me ML courses" -> task
- "Plan my day" -> task
- "Hi" -> chat

User message: {message}

Respond with ONLY one word: "chat" or "task"."""

async def router_node(state: AgentState) -> AgentState:
    llm = get_llm()
    message = state["messages"][-1].content
    response = await llm.ainvoke(ROUTER_PROMPT.format(message=message))
    raw = response.content.strip().lower()
    intent = "task" if "task" in raw else "chat"
    return {**state, "intent": intent}
