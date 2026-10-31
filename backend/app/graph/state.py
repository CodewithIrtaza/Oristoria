"""LangGraph state definition.

Uses MessagesState (add-messages reducer) from langgraph.
"""
from langgraph.graph import MessagesState  # noqa: F401 – re-exported

# MessagesState is the state type used throughout the graph.
# It provides an 'messages' key with the add-messages reducer.
