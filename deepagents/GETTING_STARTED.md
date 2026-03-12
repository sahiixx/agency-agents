# 🤖 Getting Started with Deep Agents

Welcome to the **Deep Agents** integration! This guide will help you get up and running with the autonomous agent harness.

## 📦 Installation

Deep Agents is built on top of LangChain and LangGraph. To use the integrated SDK, follow these steps:

1.  **Navigate to the Deep Agents directory**:
    ```bash
    cd deepagents/libs/deepagents
    ```

2.  **Install dependencies**:
    We recommend using `pip` or `uv` for fast installation.
    ```bash
    pip install -e .
    ```

## 🚀 Your First Autonomous Agent

Here's how to create an agent that uses one of the **Agency** personalities to perform a complex task.

```python
import os
from deepagents import create_deep_agent

# 1. Load an Agency personality (e.g., Frontend Developer)
personality_path = "../../engineering/engineering-frontend-developer.md"
with open(personality_path, "r") as f:
    system_prompt = f.read()

# 2. Define your tools (optional)
def web_search(query: str):
    """Search the web for information."""
    return f"Searching for: {query}..."

# 3. Create the Deep Agent
agent = create_deep_agent(
    tools=[web_search],
    system_prompt=system_prompt,
    model="gpt-4o" # Or any other supported model
)

# 4. Run the agent
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "Analyze the latest React performance best practices and suggest a plan for our dashboard."}
    ]
})

print(result["messages"][-1].content)
```

## 🛠️ Core Capabilities

-   **Built-in Planning**: The agent automatically decomposes complex tasks into smaller steps.
-   **Filesystem Management**: Use the integrated filesystem tools to manage context and persistent data.
-   **Subagent Spawning**: For massive tasks, the agent can spawn specialized subagents to handle specific sub-tasks.
-   **Long-term Memory**: Persist state across different threads and sessions.

## 🧪 Explore Examples

Check out the `/deepagents/examples` directory for advanced implementations:
-   **Deep Research**: A full-blown research agent.
-   **Content Builder**: A multi-agent system for content creation.
-   **NVIDIA Integration**: Optimized workflows for NVIDIA's AI stack.

---
*For more detailed information, see [README_DEEPAGENTS.md](README_DEEPAGENTS.md) and [AGENTS.md](AGENTS.md).*
