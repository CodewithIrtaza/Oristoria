"""Graph nodes: agent (and, later, tools).

Task 2 implements the single `agent` node: trim history to a token
budget, then invoke the chat model. Tool binding, dynamic system
prompts and the `tools` node arrive with Task 7.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, trim_messages
from langgraph.runtime import Runtime
from pydantic import BaseModel

from app.config import settings


class AgentContext(BaseModel):
    """Per-run context passed as the compiled graph's context_schema."""

    conversation_id: str


def make_agent_node(
    model: BaseChatModel,
    system_prompt: str | None = None,
) -> Callable[[dict[str, list[BaseMessage]], Runtime[AgentContext]], Any]:
    """Build the async agent node bound to a chat model instance."""

    async def agent_node(
        state: dict[str, list[BaseMessage]], runtime: Runtime[AgentContext]
    ) -> dict:
        history = state["messages"]
        trimmed: list[BaseMessage] = trim_messages(
            history,
            token_counter=len,  # rough char budget; fine until Task 7
            max_tokens=settings.history_token_budget,
            strategy="last",
            start_on="human",
            allow_partial=False,
            include_system=True,
        )
        messages = [*trimmed]
        if system_prompt is not None:
            messages = [SystemMessage(content=system_prompt), *messages]
        reply = await model.ainvoke(
            messages,
            config={
                "configurable": {
                    "conversation_id": runtime.context.conversation_id,
                }
            },
        )
        return {"messages": [reply]}

    return agent_node


def user_message(content: str) -> HumanMessage:
    """Wrap raw input text as a HumanMessage for graph input."""
    return HumanMessage(content=content)
