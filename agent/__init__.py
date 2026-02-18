"""
LangGraph multi-agent system for design system UI generation.

Architecture: 4 Agents, 6 Tools
  - Agent 1: Orchestrator (Supervisor StateGraph)
  - Agent 2: Discovery (list_components, get_component_spec)
  - Agent 3: Generation (get_design_tokens, preview_component)
  - Agent 4: QA (verify_quality, check_accessibility)
"""
