import os
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

# 1. Load the Technical Researcher personality (adapted from Agency's UX Researcher)
with open("design/design-ux-researcher.md", "r") as f:
    personality = f.read()

# 2. Define research tools
@tool
def search_academic_papers(query: str):
    """Searches for academic papers on a given topic."""
    # Simulated response for demonstration
    return f"Academic findings for '{query}': AI agents are evolving towards autonomous planning and tool-use."

@tool
def analyze_market_trends(topic: str):
    """Analyzes current market trends for a specific technology."""
    # Simulated response for demonstration
    return f"Market trends for '{topic}': 70% of enterprises plan to deploy autonomous agents by 2027."

# 3. Initialize the model
llm = ChatOpenAI(model="gpt-4.1-mini")

# 4. Create the Research Agent
agent = create_deep_agent(
    tools=[search_academic_papers, analyze_market_trends],
    system_prompt=personality,
    model=llm
)

# 5. Execute the mission
print("--- Starting Deep Research Mission: The Future of Autonomous Agents ---")
response = agent.invoke({
    "messages": [
        {"role": "user", "content": "Conduct a deep research mission on the future of autonomous agents. Combine academic findings with market trends and provide a summary."}
    ]
})

# 6. Display the report
print("\nDeep Research Report:\n")
print(response["messages"][-1].content)
