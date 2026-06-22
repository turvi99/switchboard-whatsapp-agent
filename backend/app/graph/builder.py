"""
Wires the nodes in `nodes.py` into the StateGraph described in Task 3:

    Acknowledge -> Context Retriever -> LLM Reasoning -> [Dispatcher | Human Handover] -> END

`compiled_graph` is built once at import time and reused for every inbound
webhook - LangGraph graphs are stateless/reentrant by design, all per-request
data lives in the AgentState dict passed into `.ainvoke()`.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    acknowledge_node,
    context_retriever_node,
    dispatcher_node,
    human_handover_node,
    llm_reasoning_node,
    route_after_reasoning,
)
from app.graph.state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("acknowledge", acknowledge_node)
    graph.add_node("context_retriever", context_retriever_node)
    graph.add_node("llm_reasoning", llm_reasoning_node)
    graph.add_node("dispatcher", dispatcher_node)
    graph.add_node("human_handover", human_handover_node)

    graph.set_entry_point("acknowledge")
    graph.add_edge("acknowledge", "context_retriever")
    graph.add_edge("context_retriever", "llm_reasoning")
    graph.add_conditional_edges(
        "llm_reasoning",
        route_after_reasoning,
        {"dispatcher": "dispatcher", "human_handover": "human_handover"},
    )
    graph.add_edge("dispatcher", END)
    graph.add_edge("human_handover", END)

    return graph.compile()


compiled_graph = build_graph()
