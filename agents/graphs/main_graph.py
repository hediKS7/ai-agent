from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes.planner import planner_node
from agents.nodes.executor import executor_node
from agents.nodes.reflector import reflector_node
from agents.nodes.memory_retriever import memory_node
from agents.nodes.memory_saver import memory_saver_node
from agents.nodes.extract_facts import extract_facts_node
from agents.nodes.retrieve_candidates import retrieve_candidates_node
from agents.nodes.memory_decision import memory_decision_node
from agents.nodes.memory_manager import memory_manager_node
from agents.nodes.router import router_node
from agents.nodes.chat_reply import chat_reply_node
from agents.nodes.task_response import task_response_node
from agents.nodes.sentiment_node import sentiment_node

def route_intent(state: AgentState) -> str:
    return "chat" if state["intent"] == "chat" else "task"

def should_continue(state: AgentState) -> str:
    if state["current_step"] < len(state["plan"]):
        return "execute"
    return "reflect"

def build_agent_graph():
    graph = StateGraph(AgentState)

    # READ + EMOTION
    graph.add_node("retrieve_memory",     memory_node)
    graph.add_node("detect_sentiment",    sentiment_node)
    graph.add_node("route_intent",        router_node)

    # RESPONSE
    graph.add_node("chat_reply",          chat_reply_node)
    graph.add_node("plan",                planner_node)
    graph.add_node("execute",             executor_node)
    graph.add_node("reflect",             reflector_node)
    graph.add_node("task_response",       task_response_node)

    # WRITE — Dynamic Memory Manager
    graph.add_node("save_message",        memory_saver_node)
    graph.add_node("extract_facts",       extract_facts_node)
    graph.add_node("retrieve_candidates", retrieve_candidates_node)
    graph.add_node("memory_decision",     memory_decision_node)
    graph.add_node("memory_manager",      memory_manager_node)

    # ── READ ──
    graph.set_entry_point("retrieve_memory")
    graph.add_edge("retrieve_memory",     "detect_sentiment")
    graph.add_edge("detect_sentiment",    "route_intent")

    # ── RESPONSE ──
    graph.add_conditional_edges("route_intent", route_intent, {
        "chat": "chat_reply",
        "task": "plan"
    })
    graph.add_edge("plan",           "execute")
    graph.add_conditional_edges("execute", should_continue, {
        "execute": "execute",
        "reflect": "reflect"
    })
    graph.add_edge("reflect",        "task_response")

    # ── WRITE ──
    graph.add_edge("chat_reply",     "save_message")
    graph.add_edge("task_response",  "save_message")
    graph.add_edge("save_message",   "extract_facts")
    graph.add_edge("extract_facts",  "retrieve_candidates")
    graph.add_edge("retrieve_candidates", "memory_decision")
    graph.add_edge("memory_decision", "memory_manager")
    graph.add_edge("memory_manager", END)

    return graph.compile()

agent_graph = build_agent_graph()
