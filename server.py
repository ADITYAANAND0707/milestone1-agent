"""
Milestone 1: Design System MCP Server.
Exposes our component library and tokens so Claude Code can generate UI from prompts.
Run with HTTP transport for: claude mcp add --transport http <name> http://127.0.0.1:3845/mcp
"""

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Path to design-system data (works when run from project root or Docker)
ROOT = Path(__file__).resolve().parent
DESIGN_SYSTEM_DIR = ROOT / "design_system"

mcp = FastMCP(
    "Design System",
    json_response=True,
)


def _load_json(name: str) -> dict | list:
    path = DESIGN_SYSTEM_DIR / f"{name}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- Resources: design system data for context ---

@mcp.resource("design-system://tokens")
def get_tokens_resource() -> str:
    """Design tokens: colors, typography, spacing, radius. Use these when generating UI."""
    data = _load_json("tokens")
    return json.dumps(data, indent=2)


@mcp.resource("design-system://components")
def get_components_resource() -> str:
    """Catalog of available components with props and import paths. Use these when generating UI."""
    data = _load_json("catalog")
    return json.dumps(data, indent=2)


# --- Tools: for Claude to query and generate UI ---

@mcp.tool()
def list_components() -> list[dict]:
    """
    List all components in our design system. Returns name, description, and props for each.
    Use this to choose which component to use for a prompt.
    """
    data = _load_json("catalog")
    return data.get("components", [])


@mcp.tool()
def get_design_tokens() -> dict:
    """
    Get design tokens (colors, typography, spacing, radius). Use these values in generated code.
    """
    return _load_json("tokens")


@mcp.tool()
def get_component_spec(component_name: str) -> dict | None:
    """
    Get full spec for one component: props, description, import path.
    component_name: e.g. Button, Input, Card
    """
    data = _load_json("catalog")
    for c in data.get("components", []):
        if c.get("name", "").lower() == component_name.lower():
            return c
    return None


@mcp.tool()
def generate_ui(prompt: str) -> str:
    """
    Generate a UI snippet from a natural-language prompt using our design system.
    Use the design-system resources/tools (tokens, list_components, get_component_spec) for context,
    then return React/TSX code that uses our components and tokens.
    prompt: e.g. "A form with email and password fields and a submit button"
    """
    tokens = _load_json("tokens")
    catalog = _load_json("catalog")
    components = catalog.get("components", [])

    # Build context string for the prompt
    tokens_str = json.dumps(tokens, indent=2)
    comps_str = json.dumps([{"name": c["name"], "description": c["description"], "props": c["props"], "import": c["import"]} for c in components], indent=2)

    instruction = f"""Generate React/TSX code for this request: "{prompt}"

Use ONLY our design system:

Design tokens (use these for colors, spacing, typography):
{tokens_str}

Available components (use these imports and props):
{comps_str}

Rules:
- Use the component imports and prop names exactly as listed.
- Use token values (e.g. colors.primary[500], spacing[4]) where relevant.
- Keep the snippet self-contained and production-quality.
- Export a single component or fragment that satisfies the prompt.
"""
    return instruction


if __name__ == "__main__":
    # Streamable HTTP. Docker maps host 3845 -> 8000 for Claude Code.
    port = int(os.environ.get("MCP_PORT", "8000"))
    try:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    except TypeError:
        # SDK may not accept host/port; default listens on 8000
        mcp.run(transport="streamable-http")
