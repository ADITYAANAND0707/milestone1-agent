"""
Agent 1: Orchestrator (Supervisor)

Custom LangGraph StateGraph that:
1. Classifies the user's request
2. Routes to the right sub-agents in the right order
3. Handles QA feedback loop (retry generation if QA fails)

Workflows:
  "generate"  -> Discovery -> Generation -> QA (-> retry if FAIL)
  "discover"  -> Discovery only
  "review"    -> QA only
  "chat"      -> Direct LLM response
"""

import logging
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agent.discovery import run_discovery
from agent.generator import run_generation
from agent.tools import verify_quality, check_accessibility

logger = logging.getLogger(__name__)

MAX_QA_RETRIES = 2

# Pre-compiled regex for code extraction (avoids recompilation per call)
_RE_CODE_BLOCK = re.compile(r"```(?:jsx|javascript|tsx|js)?\s*\n(.*?)```", re.DOTALL)


# ────────────── State ──────────────

class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    workflow: str
    user_request: str
    discovery_output: str
    generated_code: str
    qa_result: str
    retry_count: int


# ────────────── Helpers ──────────────

def _get_last_user_message(state: OrchestratorState) -> str:
    """Extract the last HumanMessage content from state."""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage) and msg.content:
            return msg.content
    return ""


def _extract_code(text: str) -> str:
    """Extract the first code block from markdown."""
    match = _RE_CODE_BLOCK.search(text)
    return match.group(1).strip() if match else ""


def _extract_all_codes(text: str) -> list[str]:
    """Extract ALL code blocks from markdown (for variant responses)."""
    return [m.group(1).strip() for m in _RE_CODE_BLOCK.finditer(text) if m.group(1).strip()]


def _is_variant_request(text: str) -> bool:
    """Check if user is asking for multiple variants."""
    t = text.lower()
    return "variant" in t or ("different" in t and ("style" in t or "version" in t))


def _get_previous_code(state: OrchestratorState) -> str:
    """Extract the most recent generated code from conversation history.
    Looks through AI messages for the last jsx code block."""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content:
            code = _extract_code(msg.content)
            if code and len(code) > 50:
                return code
    return ""


def _get_conversation_summary(state: OrchestratorState, max_turns: int = 6) -> list:
    """Get the last N conversation turns as LangChain messages (for context)."""
    all_msgs = state.get("messages", [])
    # Skip the last message (current user request — already handled separately)
    history = all_msgs[:-1] if len(all_msgs) > 1 else []
    return history[-max_turns:] if history else []


def _summarize(text: str, max_len: int = 1500) -> str:
    """Truncate text for display."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# ────────────── Helpers: cached model singleton ──────────────

_fast_model = None


def _get_fast_model():
    """Get GPT-4o-mini for fast classification/chat tasks (cached singleton)."""
    global _fast_model
    if _fast_model is not None:
        return _fast_model
    from langchain_openai import ChatOpenAI
    _fast_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _fast_model


# ────────────── Node: Classify ──────────────

async def classify_node(state: OrchestratorState) -> dict:
    """Analyze the user's request and decide the workflow.
    Skips the LLM call if workflow is already pre-classified."""
    user_msg = _get_last_user_message(state)

    if state.get("workflow"):
        logger.info("[classify] Pre-classified as: %s (skipped LLM call)", state["workflow"])
        return {"user_request": user_msg}

    model = _get_fast_model()

    try:
        response = await model.ainvoke([
            SystemMessage(content=(
                "Classify the user's request into exactly one category. "
                "Respond with ONLY the category name.\n\n"
                '"generate" — user wants to CREATE, BUILD, GENERATE, MAKE, or MODIFY a UI component, '
                "page, dashboard, form, table, card, or any visual element. "
                "Also includes: redesign, add dark mode, make responsive, simplify, add animation.\n"
                "Examples: \"Create a login form\", \"Build a dashboard\", \"Make it more minimal\", "
                "\"Add dark mode\", \"Generate 3 variants\"\n\n"
                '"discover" — user wants to EXPLORE, LIST, or BROWSE available components or design tokens.\n'
                "Examples: \"What components are available?\", \"Show me the design tokens\", "
                "\"List all components\"\n\n"
                '"review" — user wants to REVIEW, CHECK, or AUDIT existing code.\n'
                "Examples: \"Review this code\", \"Check accessibility\"\n\n"
                '"chat" — general question, greeting, or anything NOT about building UI.\n'
                "Examples: \"Hello\", \"How does the pipeline work?\", \"Thanks\""
            )),
            HumanMessage(content=user_msg),
        ])
        category = response.content.strip().lower().strip('"').strip("'")
    except Exception as e:
        logger.error("[classify] LLM call failed: %s — defaulting to chat", e)
        category = "chat"

    if "generate" in category:
        workflow = "generate"
    elif "discover" in category:
        workflow = "discover"
    elif "review" in category:
        workflow = "review"
    else:
        workflow = "chat"

    return {"workflow": workflow, "user_request": user_msg}


# ────────────── Node: Discovery ──────────────

async def discovery_node(state: OrchestratorState) -> dict:
    """Run fast component discovery (single LLM call, no ReAct loops)."""
    user_msg = state.get("user_request") or _get_last_user_message(state)
    previous_code = _get_previous_code(state)

    result = await run_discovery(user_msg, has_previous_code=bool(previous_code))
    return {"discovery_output": result}


# ────────────── Node: Generation ──────────────

async def generation_node(state: OrchestratorState) -> dict:
    """Run fast code generation (single LLM call, no tool loops).
    For variant requests, preserves the full multi-block response."""
    user_msg = state.get("user_request") or _get_last_user_message(state)
    discovery = state.get("discovery_output", "")
    qa_feedback = state.get("qa_result", "") if state.get("retry_count", 0) > 0 else ""
    previous_code = _get_previous_code(state)

    result = await run_generation(
        user_request=user_msg,
        discovery_output=discovery,
        previous_code=previous_code,
        qa_feedback=qa_feedback,
    )

    # For variant requests, preserve the full response with all code blocks + headings
    if _is_variant_request(user_msg):
        all_codes = _extract_all_codes(result)
        if len(all_codes) > 1:
            return {"generated_code": result}

    code = _extract_code(result)
    return {"generated_code": code or result}


# ────────────── Node: QA ──────────────

async def qa_node(state: OrchestratorState) -> dict:
    """Run QA checks directly — no LLM needed, pure rule-based.
    For variant responses, QA checks the first code block."""
    import json as _json
    raw_code = state.get("generated_code", "")

    if not raw_code.strip():
        return {"qa_result": "**Verdict: FAIL** (score: 0/100)\nNo code was generated."}

    # For multi-block variant responses, QA the first block
    all_codes = _extract_all_codes(raw_code)
    code = all_codes[0] if all_codes else _extract_code(raw_code) or raw_code

    quality_raw = verify_quality.invoke({"code": code})
    access_raw = check_accessibility.invoke({"code": code})

    quality = _json.loads(quality_raw) if isinstance(quality_raw, str) else quality_raw
    access = _json.loads(access_raw) if isinstance(access_raw, str) else access_raw

    q_score = quality.get("score", 0)
    a_score = access.get("score", 0)
    combined_score = min(q_score, a_score)

    all_issues = quality.get("issues", []) + access.get("issues", [])
    has_errors = any(i.get("severity") == "error" for i in all_issues)
    verdict = "FAIL" if has_errors or combined_score < 70 else "PASS"

    parts = [f"**Verdict: {verdict}** (score: {combined_score}/100)"]
    if all_issues:
        for i, issue in enumerate(all_issues[:6], 1):
            parts.append(f"{i}. [{issue.get('rule', '?')}] {issue.get('message', '')}")

    return {"qa_result": "\n".join(parts)}


# ────────────── Node: Respond ──────────────

async def respond_node(state: OrchestratorState) -> dict:
    """Format the final response to the user."""
    workflow = state.get("workflow", "chat")

    if workflow == "generate":
        raw_code = state.get("generated_code", "")
        qa = state.get("qa_result", "")
        user_msg = state.get("user_request") or _get_last_user_message(state)

        # Check if this is a variant response with multiple code blocks
        all_codes = _extract_all_codes(raw_code)
        is_variant = _is_variant_request(user_msg) and len(all_codes) > 1

        parts = []

        if is_variant:
            parts.append(f"Here are {len(all_codes)} variants:\n")
            # Extract headings from the raw response
            headings = re.findall(r"^##\s+(.+)$", raw_code, re.MULTILINE)
            for idx, code_block in enumerate(all_codes):
                heading = headings[idx] if idx < len(headings) else f"Variant {idx + 1}"
                parts.append(f"## {heading}\n")
                parts.append(f"```jsx\n{code_block}\n```\n")
        else:
            parts.append("Here's the generated component:\n")
            code = all_codes[0] if all_codes else (_extract_code(raw_code) or raw_code)
            if code:
                parts.append(f"```jsx\n{code}\n```")

        if qa:
            if "PASS" in qa.upper():
                score_match = re.search(r"score[:\s]*(\d+)", qa)
                score_text = f" (score: {score_match.group(1)}/100)" if score_match else ""
                parts.append(f"\n**QA Review:** Passed{score_text}")
            else:
                issues = re.findall(r"\d+\.\s*\[.*?\]\s*(.*?)(?=\n\d+\.|\Z)", qa, re.DOTALL)
                if issues:
                    brief = "; ".join(i.strip()[:80] for i in issues[:3])
                    parts.append(f"\n**QA Review:** Needs fixes — {brief}")
                else:
                    parts.append(f"\n**QA Review:** {_summarize(qa, 200)}")

        response = "\n".join(parts) if parts else "Could not generate the component."
        return {"messages": [AIMessage(content=response)]}

    elif workflow == "discover":
        discovery = state.get("discovery_output", "")
        if discovery:
            # Strip any embedded code blocks from discovery to keep chat clean
            clean_discovery = re.sub(r'```[\s\S]*?```', '', discovery).strip()
            return {"messages": [AIMessage(content=clean_discovery or discovery)]}
        return {"messages": [AIMessage(content="No components found.")]}

    elif workflow == "review":
        qa = state.get("qa_result", "")
        return {"messages": [AIMessage(content=qa or "Could not review the code.")]}

    else:
        model = _get_fast_model()
        user_msg = _get_last_user_message(state)
        history_msgs = _get_conversation_summary(state, max_turns=10)

        llm_messages = [
            SystemMessage(content=(
                "You are a helpful assistant for the Milestone 1 Design System Agent project. "
                "Answer questions about the Untitled UI component library, design tokens, "
                "and the multi-agent architecture. Be concise and helpful."
            )),
        ]

        # RAG: inject relevant design system context
        try:
            from agent.rag import query as rag_query
            rag_context = rag_query(user_msg, k=3)
            if rag_context:
                llm_messages.append(
                    SystemMessage(content=f"## Relevant Design System Context\n{rag_context}")
                )
        except Exception as rag_err:
            logger.warning("[orchestrator] RAG inject skipped: %s", rag_err)

        # Include conversation history for context
        for msg in history_msgs:
            llm_messages.append(msg)
        llm_messages.append(HumanMessage(content=user_msg))

        result = await model.ainvoke(llm_messages)
        return {"messages": [AIMessage(content=result.content)]}


# ────────────── Routing Functions ──────────────

def route_after_classify(state: OrchestratorState) -> str:
    workflow = state.get("workflow", "chat")
    if workflow in ("generate", "discover"):
        return "discovery"
    if workflow == "review":
        return "qa"
    return "respond"


def route_after_discovery(state: OrchestratorState) -> str:
    if state.get("workflow") == "generate":
        return "generation"
    return "respond"


def route_after_qa(state: OrchestratorState) -> str:
    qa = state.get("qa_result", "")
    retry = state.get("retry_count", 0)
    if "FAIL" in qa.upper() and retry < MAX_QA_RETRIES:
        return "retry_generation"
    return "respond"


async def bump_retry(state: OrchestratorState) -> dict:
    """Increment retry count before re-running generation."""
    return {"retry_count": state.get("retry_count", 0) + 1}


# ────────────── Build Graph ──────────────

def create_orchestrator():
    """Create the multi-agent orchestrator graph."""

    builder = StateGraph(OrchestratorState)

    builder.add_node("classify", classify_node)
    builder.add_node("discovery", discovery_node)
    builder.add_node("generation", generation_node)
    builder.add_node("qa", qa_node)
    builder.add_node("retry_generation", bump_retry)
    builder.add_node("respond", respond_node)

    builder.set_entry_point("classify")

    builder.add_conditional_edges("classify", route_after_classify, {
        "discovery": "discovery",
        "qa": "qa",
        "respond": "respond",
    })

    builder.add_conditional_edges("discovery", route_after_discovery, {
        "generation": "generation",
        "respond": "respond",
    })

    builder.add_edge("generation", "qa")

    builder.add_conditional_edges("qa", route_after_qa, {
        "retry_generation": "retry_generation",
        "respond": "respond",
    })

    builder.add_edge("retry_generation", "generation")
    builder.add_edge("respond", END)

    return builder.compile()
