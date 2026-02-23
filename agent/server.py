"""
SSE streaming endpoint for the multi-agent system.

Provides async generator that runs the orchestrator and yields
SSE-compatible chunks for the chatbot UI.
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from agent.orchestrator import create_orchestrator

ROOT = Path(__file__).resolve().parent.parent

# Load .env
for env_path in [ROOT / ".env", ROOT / "agent" / ".env"]:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        break

# Cached compiled graph singleton (built once, reused across requests)
_graph = None


def _get_graph():
    """Get or create the compiled orchestrator graph (singleton)."""
    global _graph
    if _graph is None:
        _graph = create_orchestrator()
    return _graph


def _prepare_history(history: list | None) -> list:
    """Convert raw history dicts to LangChain messages."""
    messages = []
    if history:
        for h in history[-20:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role == "user" and content:
                messages.append(HumanMessage(content=content))
            elif role == "assistant" and content:
                messages.append(AIMessage(content=content))
    return messages


def _build_initial_state(messages: list, message: str, workflow: str, library: str = "untitledui") -> dict:
    """Build the initial orchestrator state dict."""
    return {
        "messages": messages,
        "workflow": workflow,
        "user_request": message,
        "discovery_output": "",
        "generated_code": "",
        "qa_result": "",
        "retry_count": 0,
        "library": library,
    }


async def run_agent(message: str, history: list = None, workflow: str = "") -> str:
    """Run the multi-agent orchestrator and return the final response.

    Args:
        message: User's message
        history: List of {"role": "user"|"assistant", "content": "..."} dicts
        workflow: Pre-classified workflow (generate/discover/review/chat) to skip classify LLM call

    Returns:
        The final AI response as a string
    """
    graph = _get_graph()
    messages = _prepare_history(history)
    messages.append(HumanMessage(content=message))

    result = await graph.ainvoke(_build_initial_state(messages, message, workflow))

    final_messages = result.get("messages", [])
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content

    return "No response generated."


async def run_agent_stream(message: str, history: list = None, workflow: str = "", library: str = "untitledui"):
    """Run the multi-agent orchestrator and yield SSE chunks.

    Streams LLM tokens in real-time during generation and respond nodes.

    Args:
        message: User's message
        history: Conversation history
        workflow: Pre-classified workflow to skip classify LLM call
        library: Design system library (untitledui, metafore, both)

    Yields:
        dict with {"type": "status"|"chunk"|"done"|"error", ...}
    """
    import time
    graph = _get_graph()
    messages = _prepare_history(history)
    messages.append(HumanMessage(content=message))

    initial_state = _build_initial_state(messages, message, workflow, library=library)

    status_labels = {
        "classify": "Analyzing your request...",
        "discovery": "Searching component library...",
        "generation": "Generating React code...",
        "qa": "Reviewing code quality...",
        "retry_generation": "Fixing issues, regenerating...",
        "respond": "Preparing response...",
    }

    try:
        t0 = time.time()
        final_content = ""
        streamed_respond = False
        current_node = None
        thinking_nodes = {"discovery", "generation", "retry_generation"}

        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            # Track current node + send status updates
            if kind == "on_chain_start" and name in status_labels:
                current_node = name
                elapsed = time.time() - t0
                print(f"[pipeline] {name} started at {elapsed:.1f}s")
                yield {"type": "status", "text": status_labels[name]}

            # Stream LLM tokens: "thinking" for discovery/generation, "chunk" ONLY for respond/chat
            # Tokens arriving when current_node is None (between nodes) are treated as thinking
            if kind == "on_chat_model_stream":
                chunk_data = event.get("data", {})
                chunk_obj = chunk_data.get("chunk")
                if chunk_obj and hasattr(chunk_obj, "content") and chunk_obj.content:
                    token = chunk_obj.content
                    if current_node and current_node not in thinking_nodes:
                        final_content += token
                        streamed_respond = True
                        yield {"type": "chunk", "text": token}
                    else:
                        yield {"type": "thinking", "text": token}

            # Capture formatted respond node output
            if kind == "on_chain_end" and name == "respond":
                elapsed = time.time() - t0
                print(f"[pipeline] respond finished at {elapsed:.1f}s")
                if not streamed_respond:
                    output = event.get("data", {}).get("output", {})
                    new_messages = output.get("messages", [])
                    for msg in new_messages:
                        if isinstance(msg, AIMessage) and msg.content:
                            final_content = msg.content

            if kind == "on_chain_end" and name in status_labels:
                elapsed = time.time() - t0
                print(f"[pipeline] {name} finished at {elapsed:.1f}s")
                if name == current_node:
                    current_node = None

        # Send final content as chunks if not already streamed
        if final_content and not streamed_respond:
            chunk_size = 200
            for i in range(0, len(final_content), chunk_size):
                yield {"type": "chunk", "text": final_content[i:i + chunk_size]}

        elapsed = time.time() - t0
        print(f"[pipeline] TOTAL: {elapsed:.1f}s")
        yield {"type": "done"}

    except Exception as e:
        yield {"type": "error", "error": str(e)}
