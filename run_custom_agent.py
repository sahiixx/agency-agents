#!/usr/bin/env python3
"""
Run a single agent with a custom tool — Claude-powered example.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

# Load agent personality
personality_path = REPO_ROOT / "engineering/engineering-frontend-developer.md"
system_prompt = personality_path.read_text()

# Define a custom tool
@tool
def get_tech_stack_recommendation(project_type: str) -> str:
    """Provides a modern tech stack recommendation for a given project type."""
    if "dashboard" in project_type.lower():
        return "Next.js 15, Tailwind CSS, Shadcn UI, and TanStack Query."
    return "Vite, React, and Tailwind CSS."

llm = ChatOllama(model="llama3.1", base_url="http://localhost:11434")

agent = create_deep_agent(
    tools=[get_tech_stack_recommendation],
    system_prompt=system_prompt,
    model=llm
)

print("--- Running Autonomous Frontend Agent (Claude-Powered) ---")
response = agent.invoke({
    "messages": [{"role": "user", "content": (
        "I need to build a high-performance analytics dashboard. "
        "What tech stack do you recommend and what should be my first three steps?"
    )}]
})
print("\nAgent Response:\n")
print(response["messages"][-1].content)
