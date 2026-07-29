from agents.llm import get_llm
from agents.state import AgentState
from agents.prompts import AGENT_CONFIGS
from agents.pcl import apply_pcl
from agents.sentiment import enforce_response_length
from agents.followup import extract_user_commitment, needs_weekly_summary, build_weekly_summary

CHAT_PROMPT = """{system_prompt}

--- MEMORY ---
{memory_section}
--- END MEMORY ---

--- CONVERSATION HISTORY ---
{history_section}
--- END HISTORY ---

--- EMOTIONAL STATE ---
{sentiment_context}
--- END EMOTIONAL STATE ---

RESPONSE RULES:
- Obey the emotional state above. It is not optional.
- very_short: one or two sentences. Stop there.
- short: two to three sentences. Stop there.
- slow pacing: shorter sentences, more space, softer words.
- fast pacing: direct, energizing, no warm-up.
- If SUSTAINED DISTRESS is active: ground first. No advice. No tasks. No planning.
- Vary sentence length and rhythm. Mix short punchy lines with longer ones. Fragments are fine when they land.
- Cut every sentence that doesn't earn its place. No filler. No "I hope this helps." No "Feel free to ask."
- Plain text only. No markdown, no bold, no bullet symbols.
- If user says "hi": one sentence. Nothing more.

User message: {message}"""

USER_FACT_PATTERNS = [
    "i am currently", "i now live", "i moved to", "i live in",
    "i work at", "i just started", "i am now", "i recently",
    "my new", "i switched to", "i finished"
]

CONVERSATION_QUERIES = [
    "what did we talk", "what did we discuss", "what have we talked",
    "what was our conversation", "remind me what", "recap", "what did we say"
]

async def chat_reply_node(state: AgentState) -> AgentState:
    llm = get_llm()  # Use Groq for speed — Mistral only for PCL and synthesis
    message = state["messages"][-1].content
    memory_context = state.get("memory_context", "").strip()
    agent_type = state.get("agent_type", "general")
    config = AGENT_CONFIGS.get(agent_type, AGENT_CONFIGS["general"])
    history = state.get("conversation_history", [])
    sentiment_context = state.get("sentiment_context", "")

    msg_lower = message.lower().strip()
    is_greeting = msg_lower in ["hi", "hello", "hey", "bonjour", "salut", "hola"]
    is_user_stating_fact = any(p in msg_lower for p in USER_FACT_PATTERNS)
    is_recap = any(phrase in msg_lower for phrase in CONVERSATION_QUERIES)

    if is_recap:
        memory_section = "ONLY USE HISTORY — do not reference any memory."
    elif is_greeting:
        memory_section = "No memory needed for a greeting."
    elif is_user_stating_fact:
        memory_section = "User is stating a new fact. Accept it. Do not contradict with old memory."
    elif memory_context and memory_context != "NO_MEMORY_THIS_IS_CONVERSATION_RECAP":
        lines = memory_context.split("\n")
        verified = []
        capturing = False
        for line in lines:
            if "VERIFIED" in line or "profile" in line.lower():
                capturing = True
            elif "Past" in line or "episodic" in line.lower():
                capturing = False
            if capturing:
                verified.append(line)
        memory_section = "\n".join(verified) if verified else memory_context
    else:
        memory_section = "No relevant memory for this message."

    if history and not is_greeting:
        lines = []
        for msg in history[-4:]:
            role = "User" if msg["role"] == "user" else "You"
            lines.append(f"{role}: {msg['content'][:150]}")
        history_section = "\n".join(lines)
    else:
        history_section = "Start of conversation."

    response = await llm.ainvoke(CHAT_PROMPT.format(
        system_prompt=config["system_prompt"],
        message=message,
        memory_section=memory_section,
        history_section=history_section,
        sentiment_context=sentiment_context or "Neutral state detected."
    ))
    draft = response.content.replace("\u2014", ",").replace("\u2013", "-")

    if is_greeting:
        return {**state, "final_response": draft}

    final_response = await apply_pcl(
        draft_response=draft,
        user_message=message,
        agent_type=agent_type
    )

    sentiment = state.get("sentiment", {})
    sustained = state.get("sustained_pattern", {})

    # Enforce response length from sentiment
    response_length = sentiment.get("response_length", "medium")
    if response_length == "very_short":
        final_response = enforce_response_length(final_response, 2)
    elif response_length == "short":
        final_response = enforce_response_length(final_response, 3)

    # If sustained distress, strip any advice/task language
    if sustained and sustained.get("active"):
        import re
        advice_patterns = [
            r"(?i)you should\b", r"(?i)try\b", r"(?i)why don't you\b",
            r"(?i)have you considered\b", r"(?i)maybe you could\b",
            r"(?i)let me suggest\b", r"(?i)here are a few\b"
        ]
        for pat in advice_patterns:
            if re.search(pat, final_response):
                final_response = re.sub(pat, "", final_response).strip()
                break

    # Extract commitments (fire-and-forget)
    conv_id = state.get("conversation_id")
    if conv_id and agent_type == "inspirer":
        await extract_user_commitment(message, state["user_id"], conv_id)

    # Check Vibber weekly summary (fire-and-forget)
    if agent_type == "vibber":
        try:
            if await needs_weekly_summary(state["user_id"]):
                summary = await build_weekly_summary(state["user_id"])
                if summary:
                    print(f"[Vibber] Weekly summary ready: {summary[:80]}...")
        except Exception:
            pass

    return {**state, "final_response": final_response}
