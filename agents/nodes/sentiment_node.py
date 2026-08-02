from agents.nlp.sentiment import analyze_sentiment
from agents.sentiment import save_emotional_state, get_emotional_pattern, get_sustained_pattern, build_sentiment_context
from agents.state import AgentState

async def sentiment_node(state: AgentState) -> AgentState:
    """
    Detect emotional state from the user's message.
    Runs before response generation so all agents can adapt tone/pacing.
    """
    message = state["messages"][-1].content
    user_id = state["user_id"]

    sentiment = analyze_sentiment(message)
    pattern = await get_emotional_pattern(user_id, days=7)
    sustained = await get_sustained_pattern(user_id, lookback=5)

    # Save to history (async, non-blocking)
    try:
        await save_emotional_state(
            user_id=user_id,
            emotion=sentiment.get("emotion", "neutral"),
            intensity=sentiment.get("intensity", 0.5),
            note=sentiment.get("note", "")
        )
    except Exception:
        pass

    sentiment_context = build_sentiment_context(sentiment, pattern, sustained)

    return {
        **state,
        "sentiment": sentiment,
        "sentiment_context": sentiment_context,
        "emotional_pattern": pattern,
        "sustained_pattern": sustained
    }
