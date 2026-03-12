# 👑 The Agency: Ultimate AI Agent Powerhouse

Welcome to the world's most comprehensive and integrated AI Agent Agency. This repository combines the **specialized personalities of 1,063+ agents** with the **Deep Agents autonomous harness**, creating a "Perfect" environment for building, testing, and deploying AI swarms.

---

## 🌟 Core Components

| Component | Description | Location |
| :--- | :--- | :--- |
| **Workforce** | 1,063+ specialized agent personalities across all domains. | `/design`, `/engineering`, etc. |
| **Engine** | Integrated Deep Agents SDK with planning and memory. | `/deepagents` |
| **Command Center** | CLI tools for listing, launching, and orchestrating agents. | `mission_control.py`, `swarm_orchestrator.py` |
| **Quality Gate** | Automated unit tests for agent identity and compliance. | `/tests` |
| **Scaffold** | Standardized Next.js + Tailwind templates for agent output. | `/scaffold` |

---

## 🚀 Getting Started

### 1. 🛠️ Environment Setup
Ensure you have the required dependencies installed and your API keys set.
```bash
# Install Deep Agents SDK
cd deepagents/libs/deepagents && pip install -e .

# Set your API Key
export OPENAI_API_KEY="your_openai_api_key"
export PYTHONPATH=$PYTHONPATH:$(pwd)/deepagents/libs/deepagents
```

### 2. 📡 Mission Control CLI
Discover and launch any agent personality with a single command.
```bash
# List all available agents
python3 mission_control.py --list

# Launch a specific agent
python3 mission_control.py --agent engineering/engineering-frontend-developer.md --query "Design a login page"
```

### 3. 🐝 Swarm Orchestration
Launch a multi-agent team (PM + Dev + QA) to handle complex, end-to-end missions.
```bash
python3 swarm_orchestrator.py --mission "Build a high-performance analytics dashboard"
```

---

## 🛠️ Tool Integrations

The Agency's personalities are pre-converted and ready for use in your favorite agentic IDEs and CLIs.

- **Cursor**: 128 specialized `.mdc` rules in `.cursor/rules/`.
- **Aider**: Integrated conventions in `integrations/aider/CONVENTIONS.md`.
- **Windsurf**: Pre-configured rules in `integrations/windsurf/.windsurfrules`.
- **Claude Code, GitHub Copilot, & More**: See the `/integrations` folder for details.

---

## 🧪 Testing & Verification

Maintain perfection by running the automated agent test suite.
```bash
python3 tests/agent_tests.py
```

---

## 📂 Directory Structure

- `/deepagents`: The autonomous agent harness and SDK.
- `/integrations`: Converted personalities for various coding tools.
- `/scaffold`: Standardized project templates for agent builds.
- `/tests`: Unit tests for agent personalities.
- `/specialized`: High-level orchestrators like the **Perfect Agent Orchestrator**.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Perfected by Manus for the ultimate agentic experience.*
