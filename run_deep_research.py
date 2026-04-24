#!/usr/bin/env python3
"""
Deep Research Agent — Claude-powered, with real web-aware tooling stubs.
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("❌  ANTHROPIC_API_KEY not set.")
    sys.exit(1)

personality = (REPO_ROOT / "design/design-ux-researcher.md").read_text()

@tool
def search_academic_papers(query: str) -> str:
    """Searches for academic papers on a given topic."""
    return (f"Academic findings for '{query}': "
            "AI agents are evolving towards autonomous planning and tool-use. "
            "Key papers: 'ReAct' (Yao et al.), 'Toolformer' (Schick et al.), "
            "'Constitutional AI' (Anthropic, 2022).")

@tool
def analyze_market_trends(topic: str) -> str:
    """Analyzes current market trends for a specific technology."""
    return (f"Market trends for '{topic}': "
            "70% of enterprises plan to deploy autonomous agents by 2027. "
            "Claude, GPT-4, and Gemini are the dominant LLM backbones. "
            "Multi-agent frameworks (LangGraph, CrewAI, AutoGen) growing 3x YoY.")

@tool
def check_competitor_landscape(domain: str) -> str:
    """Maps the competitive landscape for a given domain."""
    return (f"Competitor landscape for '{domain}': "
            "Key players: Anthropic (Claude), OpenAI (GPT), Google (Gemini), "
            "Mistral, Cohere. Differentiation factors: safety, reasoning depth, "
            "context window, tool use, multimodality.")

llm = ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key)

agent = create_deep_agent(
    tools=[search_academic_papers, analyze_market_trends, check_competitor_landscape],
    system_prompt=personality,
    model=llm
)

print("--- Deep Research Mission: The Future of Autonomous Agents (Claude-Powered) ---")
response = agent.invoke({
    "messages": [{"role": "user", "content": (
        "Conduct a deep research mission on the future of autonomous agents. "
        "Combine academic findings, market trends, and competitor landscape. "
        "Produce a structured summary with key insights and recommendations."
    )}]
})
print("\nDeep Research Report:\n")
print(response["messages"][-1].content)
