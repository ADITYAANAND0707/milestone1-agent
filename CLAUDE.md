# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that exposes a design system to Claude Code. It allows Claude Code to generate React/TSX UI components using a custom component library and design tokens through natural language prompts.

**Architecture**: Python FastMCP server → exposes design system data (tokens, components) → Claude Code queries via HTTP transport → generates UI code following the design system.

## Running the MCP Server

### Docker (Recommended)
```bash
docker compose up --build
```
- Server runs at `http://127.0.0.1:3845/mcp`
- Leave terminal open while server is running
- Stop with `Ctrl+C`

### Local Python
```bash
pip install -r requirements.txt
python server.py
```
- Server runs at `http://127.0.0.1:8000/mcp`
- Stop with `Ctrl+C`

### Dashboard UI
```bash
cd dashboard
python server.py
```
- Opens at `http://127.0.0.1:3850`
- Provides status checks, command copying, and prompt building

## Claude Code Integration

### Register the server
```bash
# With Docker (port 3845)
claude mcp add --transport http design-system http://127.0.0.1:3845/mcp

# With local Python (port 8000)
claude mcp add --transport http design-system http://127.0.0.1:8000/mcp
```

### Verify registration
```bash
claude mcp list
```

### Remove the server
```bash
claude mcp remove design-system
```

## Key Architecture

### MCP Server (server.py)
- Uses FastMCP library with HTTP transport
- Exposes resources and tools to Claude Code
- Loads design system data from `design_system/` JSON files
- Port 8000 by default (configurable via `MCP_PORT` env var)
- Docker maps host port 3845 → container port 8000

### Resources
Resources provide context to Claude Code:
- `design-system://tokens` - Design tokens (colors, typography, spacing, radius)
- `design-system://components` - Component catalog (Button, Input, Card with props)

### Tools
Tools that Claude Code can invoke:
- `list_components()` - List all available components with descriptions and props
- `get_design_tokens()` - Retrieve all design tokens
- `get_component_spec(component_name)` - Get full spec for a specific component
- `generate_ui(prompt)` - Generate UI code from natural language prompt

### Design System Data
Located in `design_system/`:
- `tokens.json` - Colors, typography (font family/size/weight), spacing, border radius
- `catalog.json` - Component definitions with name, description, props, and import paths

**To customize**: Edit these JSON files to match your actual component library. The provided data is example/PoC data.

### TypeScript Client (src/mcp-client.ts)
Programmatic MCP client for accessing the design system server from TypeScript/Node.js applications. Provides functions to connect, list tools/resources, call tools, and read resources.

### Dashboard (dashboard/)
Single-page UI for managing the MCP server:
- `index.html` - Dashboard interface
- `server.py` - Serves dashboard at port 3850, provides `/api/status` endpoint to check if MCP server (port 3845) is running

## Port Configuration

- **8000**: Default MCP server port (local Python)
- **3845**: Docker-mapped MCP server port (recommended for Claude Code)
- **3850**: Dashboard server port

## Workflow

1. Start MCP server (Docker or local Python)
2. Register server with Claude Code
3. In Claude Code, request UI generation: "Create a login form using our design system"
4. Claude Code queries design system resources/tools and generates React/TSX code using the defined components and tokens
