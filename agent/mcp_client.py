"""
FastMCP client for connecting to the MCP server (tools 1-3).

In M1: Used as a reference. Agents use direct tools from tools.py.
In M2: This pattern maps to Ctrlagent Maker Integrations.

Usage (when MCP server is running on port 8000):
    tools = await load_mcp_tools_from_server()
"""

import asyncio
from langchain_mcp_adapters.tools import load_mcp_tools

MCP_SERVER_URL = "http://localhost:8000/mcp"


async def load_mcp_tools_from_server(url: str = MCP_SERVER_URL):
    """Load LangChain tools from a running MCP server.

    Returns a list of LangChain tools wrapping MCP server endpoints.
    Requires: MCP server running at the given URL.
    """
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                return tools
    except Exception as e:
        print(f"[mcp_client] Could not connect to MCP server at {url}: {e}")
        print("[mcp_client] Falling back to direct tools from tools.py")
        from agent.tools import list_components, get_component_spec, get_design_tokens
        return [list_components, get_component_spec, get_design_tokens]
