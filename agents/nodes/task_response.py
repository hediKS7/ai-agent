from agents.llm import get_llm
from agents.state import AgentState
from agents.prompts import AGENT_CONFIGS
from agents.pcl import apply_pcl
from agents.sentiment import enforce_response_length
from agents.followup import extract_user_commitment

SYNTHESIS_PROMPT = """{system_prompt}

Emotional state of user: {sentiment_context}
Adapt your tone and length accordingly. Plain text only, no markdown.
If sustained distress is active: respond in two sentences max, no advice.

The user asked: {goal}

Here is the research gathered:
{results}

Write a concise, natural response in flowing prose — no bullet points, no dashes, no numbered lists, no bold headers.
Write like a knowledgeable friend explaining something clearly in 3-5 sentences.
Get to the point immediately. Never use em dashes (—) or en dashes (–) — use commas or periods instead. No introduction, no "here are the top X", no closing offer to help further."""

async def task_response_node(state: AgentState) -> AgentState:
    llm = get_llm(prefer_mistral=True)
    agent_type = state.get("agent_type", "general")
    config = AGENT_CONFIGS.get(agent_type, AGENT_CONFIGS["general"])
    goal = state["messages"][-1].content
    results = "\n\n".join(
        f"{r['step']}: {r['output']}" for r in state["tool_results"]
    )
    sentiment_context = state.get("sentiment_context", "Neutral.")
    response = await llm.ainvoke(SYNTHESIS_PROMPT.format(
        system_prompt=config["system_prompt"],
        goal=goal,
        results=results,
        sentiment_context=sentiment_context
    ))
    draft_response = response.content

    final_response = await apply_pcl(
        draft_response=draft_response,
        user_message=goal,
        agent_type=agent_type
    )

    sentiment = state.get("sentiment", {})
    sustained = state.get("sustained_pattern", {})
    response_length = sentiment.get("response_length", "medium")
    if response_length in ("very_short", "short"):
        max_sent = 2 if response_length == "very_short" else 3
        final_response = enforce_response_length(final_response, max_sent)

    if sustained and sustained.get("active"):
        import re
        for pat in [r"(?i)you should\b", r"(?i)try\b", r"(?i)have you considered\b"]:
            final_response = re.sub(pat, "", final_response).strip()

    # Extract commitments if Inspirer
    conv_id = state.get("conversation_id")
    if conv_id and agent_type == "inspirer":
        await extract_user_commitment(goal, state["user_id"], conv_id)

    return {**state, "final_response": final_response}
