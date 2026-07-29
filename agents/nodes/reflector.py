# agents/nodes/reflector.py
from agents.llm import get_llm
from agents.state import AgentState

async def reflector_node(state: AgentState) -> AgentState:
    # Use Mistral for reflection — better reasoning on longer context
    llm = get_llm(prefer_mistral=True)
    results_str = "\n".join([str(r) for r in state["tool_results"]])
    prompt = f"""Review these task execution results:

Plan: {state['plan']}
Results: {results_str}

Is the task complete? What improvements can be made? Give a final summary."""

    response = await llm.ainvoke(prompt)
    return {**state, "reflection": response.content}