from typing import TypedDict, Annotated, List, Optional, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    conversation_history: List[dict]
    user_id: str
    task_id: str
    conversation_id: Optional[str]
    intent: str
    agent_type: str
    plan: List[str]
    current_step: int
    tool_results: List[dict]
    reflection: str
    final_response: str
    needs_clarification: bool
    clarification_question: str
    memory_context: str
    candidate_memories: List[dict]
    memory_actions: Optional[Any]
    sentiment: Optional[dict]
    sentiment_context: str
    emotional_pattern: Optional[dict]
    sustained_pattern: Optional[dict]
