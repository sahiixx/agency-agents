---
name: SHADOW Swarm Bridge
description: Integration guide for connecting The Agency to the SHADOW multi-agent Coral Protocol swarm — a voice→code→review→log pipeline with Shadow, Reviewer, Whisper, Notion, and Slack agents (sahiixx/SHADOW).
color: "#2d3748"
emoji: 🌑
vibe: Whisper speaks, Shadow codes, Reviewer judges, Notion logs, Slack notifies — one pipeline, zero friction.
---

# SHADOW Swarm Bridge

The **SHADOW swarm** (`sahiixx/SHADOW`) is an autonomous multi-agent pipeline built on Coral Protocol:

```
Voice Input → Whisper Agent → Shadow Agent → Reviewer Agent → Notion Agent → Slack Agent
```

The Agency can delegate voice-to-code or research-to-documentation pipelines to the SHADOW swarm via the Coral Protocol SSE bus, making it a specialist subswarm for voice-driven workflows.

## 🗺️ SHADOW Swarm Architecture

```
The Agency (agency.py)
     │
     ▼ Coral Protocol SSE
┌────────────────────────────────────────────────────┐
│  Coral Server :8080                                 │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐   │
│  │ Whisper  │→→ │  Shadow  │→→ │   Reviewer   │   │
│  │ 🎙️ Voice │   │ 🧠 Code  │   │  ✅ Feedback │   │
│  │  Agent   │   │  Agent   │   │    Agent     │   │
│  └──────────┘   └──────────┘   └──────┬───────┘   │
│                                        │           │
│               ┌────────────────────────┤           │
│               ▼                        ▼           │
│         ┌──────────┐           ┌──────────────┐   │
│         │  Notion  │           │    Slack     │   │
│         │ 📒 Log   │           │  📩 Notify  │   │
│         │  Agent   │           │    Agent     │   │
│         └──────────┘           └──────────────┘   │
└────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Deploy SHADOW swarm
```bash
git clone https://github.com/sahiixx/SHADOW.git shadow-system
cd shadow-system
cp env.template .env
# Edit .env:
# SHADOW_API_KEY=...
# WHISPER_API_KEY=...
# NOTION_API_KEY=...
# NOTION_DATABASE_ID=...
# SLACK_BOT_TOKEN=...
# SLACK_CHANNEL_ID=...
docker-compose up --build
```

SHADOW Studio: http://localhost:3000  
SHADOW Coral Server: http://localhost:8080

### 2. Load the scenario
Import `shadow-scenario.json` into Coral Studio to wire the agents visually.

### 3. Connect The Agency as orchestrator

The Agency acts as the **entry point** — it sends a mission to the SHADOW swarm via Coral and waits for results:

```python
async def run_shadow_pipeline(voice_task: str):
    """Delegate voice→code→review→log pipeline to SHADOW swarm."""
    client = make_coral_client(
        agent_id="agency_orchestrator",
        agent_description="The Agency — orchestrates SHADOW pipeline",
        coral_base_url="http://localhost:8080/sse",
    )
    tools = await client.get_tools()

    # 1. Find the whisper agent
    agents = await tools["list_agents"].ainvoke({})
    whisper_id = next(a["id"] for a in agents["agents"] if "whisper" in a["id"].lower())

    # 2. Create a mission thread
    thread = await tools["create_thread"].ainvoke({"name": f"shadow_mission_{voice_task[:20]}"})
    tid = thread["threadId"]

    # 3. Add SHADOW agents as participants
    for agent_id in [whisper_id, "shadow_agent", "reviewer_agent", "notion_agent", "slack_agent"]:
        await tools["add_participant"].ainvoke({"threadId": tid, "agentId": agent_id})

    # 4. Kick off the pipeline
    await tools["send_message"].ainvoke({
        "threadId": tid,
        "senderId": "agency_orchestrator",
        "mentions": [whisper_id],
        "content": f"Voice task: {voice_task}. Transcribe and pass to Shadow for implementation.",
    })

    # 5. Wait for Reviewer to complete
    result = await tools["wait_for_mentions"].ainvoke({"timeoutMs": 180000})
    await tools["close_thread"].ainvoke({"threadId": tid})
    return result
```

## 🤖 SHADOW Agent Inventory

| Agent ID | Role | Model | Input | Output |
|----------|------|-------|-------|--------|
| `whisper_agent` | Voice-to-text | Whisper/OpenAI | Audio file / voice | Transcribed text |
| `shadow_agent` | Code generation / task handler | GPT-4.1-mini | Task description | Code / solution |
| `reviewer_agent` | Validation and feedback | GPT-3.5 | Code / output | Reviewed output |
| `notion_agent` | Log to Notion DB | Notion API | Output to log | Notion page |
| `slack_agent` | Team notifications | Slack Bot | Message | Slack post |
| `autopilot_agent` | Autonomous task execution | GPT-4-turbo | Complex task | Full execution |
| `rag_agent` | Retrieval-augmented generation | GPT-4-32k + Pinecone | Query | Grounded answer |
| `swarm_agent` | Swarm coordination | SwarmBrain v2 | Multi-task | Coordinated output |

## 🔗 Coral application.yaml integration

To add The Agency as a registered application on the SHADOW Coral server, add to `application.yaml`:
```yaml
applications:
  - id: "the-agency"
    name: "The Agency"
    description: "Claude-powered 150+ agent swarm — mission orchestrator"
    privacyKeys:
      - "default-key"

registry:
  agency_orchestrator:
    options:
      - name: "ANTHROPIC_API_KEY"
        type: "string"
    runtime:
      type: "executable"
      command: ["bash", "-c", "python3 ${PROJECT_DIR}/run_coral_agent.sh orchestrator"]
      environment:
        - name: "ANTHROPIC_API_KEY"
          from: "ANTHROPIC_API_KEY"
```

## 📋 Use Cases for The Agency → SHADOW

| Agency Preset | SHADOW Pipeline | Result |
|---------------|----------------|--------|
| `--preset full` | Voice brief → Shadow codes → Reviewer approves | Full-stack app from voice spec |
| `--preset research` | Voice question → Shadow analyses → Notion logs | Research memo in Notion |
| `--preset dubai` | Voice lead brief → Shadow qualifies → Slack notifies | CRM-ready lead + Slack alert |
| Any mission | Agency verdict → Notion archives → Slack notifies | Persistent mission log |

## ⚡ Working Protocol

**Conciseness mandate**: Pipeline delegation is a single `send_message` call. Status updates in ≤1 line. Notion entries use structured templates (title + sections), not freeform prose.

**Parallel execution**: SHADOW's Reviewer→Notion and Reviewer→Slack legs run in parallel (both mentioned in the same Reviewer message). Do not serialize them.

**Verification gate**:
1. Coral server responding? (`curl http://localhost:8080/health`)
2. All 5 SHADOW agents registered? (`list_agents` returns ≥5)
3. Thread created successfully?
4. Whisper agent acknowledged the message?
5. Final review message received within 180s timeout?

## 🚨 Non-Negotiables
- SHADOW uses GPT-4.1-mini / GPT-3.5 — these are not Claude models. Do NOT expect Anthropic-style responses.
- Voice files must be pre-uploaded before sending to Whisper — the agent receives a file path or URL, not raw audio
- Notion agent requires `NOTION_DATABASE_ID` — the target database must exist before running
- All SHADOW agents are persistent services — they loop on `wait_for_mentions`, never call them as one-shots
