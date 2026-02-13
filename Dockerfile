# Milestone 1: Design System MCP Server (Python)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY design_system/ design_system/
COPY server.py .

# Host maps 3845 -> 8000 (SDK default) for Claude Code
EXPOSE 8000

CMD ["python", "server.py"]
