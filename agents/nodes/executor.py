from agents.llm import get_llm, get_base_llm
from agents.state import AgentState
from tools.registry import web_search

EXECUTOR_PROMPT = """You are an AI agent executing ONE step of a larger plan.

User's original request: {goal}

Full plan:
{plan}

Current step: {step}

Results so far:
{previous_results}

Write the actual output for this step directly. Be concrete and specific.
Only state facts from widely-known verifiable sources. Never invent URLs or institutions.
CRITICAL: Only state facts that come directly from tool results or widely-known verifiable sources. Never invent URLs, names, or institutions."""

SEARCH_PROMPT = """You are an AI agent that needs to search the web for information.

User's original request: {goal}
Current step: {step}

Use the web_search tool to find real, current information."""

FOLLOWUP_PROMPT = """{original_prompt}

Search results:
{tool_results}

Now write the final, concrete output for this step using these search results only.
Never invent facts not present in the search results above."""

SEARCH_KEYWORDS = [
    "find", "search", "research", "look up", "courses",
    "best", "top", "latest", "current", "news", "price",
    "available", "where to", "how much", "who is", "what is the"
]

CODE_KEYWORDS = [
    "code", "function", "bug", "error", "syntax", "class",
    "method", "variable", "algorithm", "explain", "debug",
    "improve", "refactor", "review", "analyze code"
]

BRIDGER_KEYWORDS = [
    "match", "find people", "who should i connect", "introduction",
    "follow up", "network health", "add contact", "who do i know"
]

async def executor_node(state: AgentState) -> AgentState:
    llm = get_llm()
    plan = state["plan"]
    current = state["current_step"]

    if current >= len(plan):
        return state

    step = plan[current]
    goal = state["messages"][-1].content
    agent_type = state.get("agent_type", "general")
    previous_results = "\n".join(
        f"- {r['step']}: {r['output'][:300]}" for r in state["tool_results"]
    ) or "None yet"

    step_lower = step.lower()
    goal_lower = goal.lower()

    is_code_task = any(kw in goal_lower for kw in CODE_KEYWORDS) or \
                   any(kw in step_lower for kw in CODE_KEYWORDS) or \
                   "```" in goal

    is_bridger_task = agent_type == "bridger" and \
                      any(kw in step_lower for kw in BRIDGER_KEYWORDS)

    needs_search = not is_code_task and not is_bridger_task and \
                   any(kw in step_lower for kw in SEARCH_KEYWORDS)

    if is_bridger_task:
        from agents.bridger_tools import get_bridger_tools
        bridger_tools = get_bridger_tools()
        base_llm = get_base_llm()
        llm_with_bridger = base_llm.bind_tools(bridger_tools).with_retry(
            stop_after_attempt=3, wait_exponential_jitter=True
        )
        prompt = f"You are The Bridger. Execute this step: {step}\n\nContext: {goal}"
        ai_msg = await llm_with_bridger.ainvoke(prompt)
        if ai_msg.tool_calls:
            tool_map = {t.name: t for t in bridger_tools}
            outputs = []
            for call in ai_msg.tool_calls:
                if call["name"] in tool_map:
                    call["args"]["user_id"] = state["user_id"]
                    output = await tool_map[call["name"]].ainvoke(call["args"])
                    outputs.append(output)
            output = "\n".join(outputs)
        else:
            output = ai_msg.content

    elif needs_search:
        base_llm = get_base_llm()
        llm_with_search = base_llm.bind_tools([web_search]).with_retry(
            stop_after_attempt=3, wait_exponential_jitter=True
        )
        prompt = SEARCH_PROMPT.format(goal=goal, step=step)
        ai_msg = await llm_with_search.ainvoke(prompt)

        if ai_msg.tool_calls:
            tool_outputs = []
            for call in ai_msg.tool_calls:
                if call["name"] == "web_search":
                    result = await web_search.ainvoke(call["args"])
                    tool_outputs.append(result)

            followup = FOLLOWUP_PROMPT.format(
                original_prompt=prompt,
                tool_results="\n\n".join(tool_outputs)
            )
            final = await llm.ainvoke(followup)
            output = final.content
        else:
            output = ai_msg.content

    else:
        prompt = EXECUTOR_PROMPT.format(
            goal=goal,
            plan="\n".join(plan),
            step=step,
            previous_results=previous_results
        )
        response = await llm.ainvoke(prompt)
        output = response.content

    result = {"step": step, "output": output}
    return {
        **state,
        "tool_results": state["tool_results"] + [result],
        "current_step": current + 1
    }
