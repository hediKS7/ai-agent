from agents.llm import get_llm
from agents.state import AgentState
from agents.prompts import AGENT_CONFIGS
from langchain_core.prompts import ChatPromptTemplate

PLANNER_PROMPT = """{system_prompt}

The user has made the following request:
{request}

Relevant memory context: {memory_context}

Create a concise plan of AT MOST 5 clear, specific, executable steps to fulfill this request.
Return ONLY a numbered list of steps, nothing else."""

async def planner_node(state: AgentState) -> AgentState:
    llm = get_llm()
    agent_type = state.get("agent_type", "general")
    config = AGENT_CONFIGS.get(agent_type, AGENT_CONFIGS["general"])

    response = await llm.ainvoke(PLANNER_PROMPT.format(
        system_prompt=config["system_prompt"],
        request=state["messages"][-1].content,
        memory_context=state.get("memory_context", "None")
    ))
    steps = [l.strip() for l in response.content.split('\n')
             if l.strip() and l.strip()[0].isdigit()]
    return {**state, "plan": steps, "current_step": 0}
