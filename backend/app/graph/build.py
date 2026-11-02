"""Graph builder: compile the LangGraph StateGraph.

Task 2 compiles a single-node graph (agent) without a checkpointer:
streaming works, and message history lands in Task 3 when
AsyncPostgresSaver is wired in. Never add an in-memory checkpointer to
this production path (Docs/AGENTS.md → Never).
"""
from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import AgentContext, make_agent_node
from app.graph.state import MessagesState
from app.llm.providers import get_chat_model


def build_graph() -> StateGraph:
    """Assemble the agent graph (uncompiled)."""
    model = get_chat_model()
    graph = StateGraph(MessagesState, context_schema=AgentContext)
    graph.add_node("agent", make_agent_node(model))
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    return graph


def compile_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Compile the graph. A Postgres checkpointer arrives with Task 3."""
    return build_graph().compile(checkpointer=checkpointer)
