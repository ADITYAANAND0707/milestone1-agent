# Plan bundle — index and prompt for online LLM

This folder contains all plan and context files so you can upload them to an online LLM (e.g. ChatGPT, Claude.ai, Gemini) and get a **single professional document** or a **reusable prompt**.

---

## Files in this folder (read in order)

| File | What it is |
|------|------------|
| **00_INDEX_AND_PROMPT.md** | This file — index + prompt to paste. |
| **01_MAKER_WIDGET_GENERATION_PLAN.md** | Main plan: what we're building, flow, 5-week timeline, RACI, risks, API contract. For product, design, engineering, leadership. |
| **02_MAKER_AND_MCP_DELIVERY_PLAN.md** | 5-week plan including **hostable MCP** for component library. MCP scope, week-by-week MCP + Maker deliverables, success criteria. |
| **03_PLAN_WEEK1_PLATFORM_INTEGRATION.md** | Week 1 only: day-by-day tasks for Person A and Person B, deliverables checklist, naming from transcripts. |
| **04_PROJECT_CONTEXT_SUMMARY.md** | Short project context: 4-agent pipeline, tools, RAG, Maker integration, team, key terms. For LLM context. |

---

## Prompt to paste into the online LLM

Copy the block below and paste it into your online LLM **after** uploading the 4 content files (01, 02, 03, 04). Adjust the output format if you want (e.g. PDF outline, Confluence, Notion).

```
I'm going to attach several markdown files that describe a 5-week delivery plan for integrating a "Maker" platform with our widget generation service and a hostable MCP server for the component library.

**What I need from you:**

1. **One professional document** that merges the content of all attached files into a single, well-structured document suitable for both technical and non-technical readers (product, design, engineering, leadership). Keep it to the point: no fluff, clear sections, tables where helpful.

2. **Suggested structure:**  
   - Executive summary / at a glance  
   - What we're building (plain language)  
   - How it works (flow + architecture)  
   - 5-week timeline with weekly and Week 1 day-by-day detail  
   - Who does what (RACI / two-person split)  
   - Contract v0 (API request/response summary)  
   - MCP scope and hostable requirements  
   - Success criteria and risks  
   - References and glossary

3. **Tone:** Professional, concise, consistent terminology (Maker, Widget Manifest, contract v0, MCP server, Person A / Person B, library param untitledui/metafore/both).

4. **Optional:** At the end, give me a short "prompt" I can reuse with another LLM or new chat to regenerate or update this document from the same source files.

Please use the attached files as the single source of truth; do not invent new deliverables or dates.
```

---

## After you get the professional doc

- You can ask the same LLM to export or reformat (e.g. "output as a Word-ready outline" or "give me bullet points for a slide deck").
- To regenerate later: re-upload 01–04 and use the same prompt, or the "short prompt" the LLM gives you at the end.
