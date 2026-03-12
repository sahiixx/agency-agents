# 🎭 The Agency + 🤖 Deep Agents: The Ultimate Agentic Powerhouse

> **A complete AI agency with a high-performance agent harness.** - This repository combines the meticulously crafted personalities of **The Agency** with the advanced planning and execution capabilities of **LangChain Deep Agents**.

[![GitHub stars](https://img.shields.io/github/stars/sahiixx/agency-agents?style=social)](https://github.com/sahiixx/agency-agents)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 What Is This?

This repository is a unique integration of two powerful agentic worlds:

1.  **[The Agency](https://github.com/msitarzewski/agency-agents)**: A collection of specialized AI agent personalities (Frontend, Backend, Marketing, etc.) with proven workflows and deliverables.
2.  **[LangChain Deep Agents](https://github.com/langchain-ai/deepagents)**: A state-of-the-art agent harness built on LangGraph that provides built-in task planning, filesystem management, subagent-spawning, and long-term memory.

**By combining them, you can take any Agency personality and give it the "brain" of a Deep Agent to execute complex, multi-step tasks autonomously.**

---

## 🛠️ How to Use

### 1. Using Agency Personalities
The agents are organized by division (Engineering, Design, Marketing, etc.). You can use them as reference prompts or integrate them into tools like Claude Code, Cursor, or Aider.

- **Claude Code**: `cp -r design/ engineering/ ... ~/.claude/agents/`
- **Cursor/Aider**: Use the `./scripts/install.sh` tool to set up integrations.

### 2. Using the Deep Agents SDK
The Deep Agents core is located in the `deepagents/` directory. You can use it to build your own autonomous agents.

```python
# Example: Creating a Deep Agent with an Agency personality
from deepagents import create_deep_agent

# Use the 'Frontend Developer' personality as a system prompt
with open('engineering/engineering-frontend-developer.md', 'r') as f:
    personality = f.read()

agent = create_deep_agent(
    tools=[...], # Add your custom tools here
    system_prompt=personality,
)

# Run the agent on a complex task
agent.invoke({"messages": [{"role": "user", "content": "Build a responsive dashboard using Tailwind CSS"}]})
```

---

## 📂 Repository Structure

- **`/design`, `/engineering`, `/marketing`, etc.**: The Agency's specialized agent personality files.
- **`/deepagents`**: The integrated LangChain Deep Agents SDK and CLI.
    - **`/deepagents/libs`**: Core SDK and partner integrations (Daytona, Modal, etc.).
    - **`/deepagents/examples`**: Notebooks and scripts demonstrating Deep Agents in action.
- **`/scripts`**: Installation and conversion scripts for various AI coding tools.

---

## 🎨 The Agency Roster

### 💻 Engineering Division
| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| 🎨 [Frontend Developer](engineering/engineering-frontend-developer.md) | React/Vue/Angular, UI implementation | Modern web apps, pixel-perfect UIs |
| 🏗️ [Backend Architect](engineering/engineering-backend-architect.md) | API design, database architecture | Server-side systems, microservices |
| 🤖 [AI Engineer](engineering/engineering-ai-engineer.md) | ML models, deployment, AI integration | AI-powered apps, data pipelines |
| ... | ... | ... |

*(See individual directories for the full roster of 50+ agents)*

---

## 🧪 Deep Agents Examples
Explore the `deepagents/examples` directory for advanced use cases:
- **Deep Research**: An agent that performs deep web research and writes reports.
- **Content Builder**: An agent that uses subagents to create blog posts and social media content.
- **NVIDIA Deep Agent**: Optimized agent for NVIDIA's stack.

---

## ⚠️ Important: GitHub Actions
The `.github/workflows/lint-agents.yml` file was removed during the initial push due to environment restrictions. To restore it, please manually create the file in your GitHub repository and paste the content from the `lint-agents.yml` file found in the root of this sandbox.

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
