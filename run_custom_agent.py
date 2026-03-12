import os
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

# 1. Load the Frontend Developer personality
personality_path = "engineering/engineering-frontend-developer.md"
with open(personality_path, "r") as f:
    system_prompt = f.read()

# 2. Define a simple tool
@tool
def get_tech_stack_recommendation(project_type: str):
    """Provides a modern tech stack recommendation for a given project type."""
    if "dashboard" in project_type.lower():
        return "Next.js 15, Tailwind CSS, Shadcn UI, and TanStack Query."
    return "Vite, React, and Tailwind CSS."

# 3. Initialize the model
# Using gpt-4o-mini for efficiency in this demonstration
llm = ChatOpenAI(model="gpt-4.1-mini")

# 4. Create the Deep Agent
agent = create_deep_agent(
    tools=[get_tech_stack_recommendation],
    system_prompt=system_prompt,
    model=llm
)

# 5. Run the agent
print("--- Running Autonomous Frontend Agent ---")
response = agent.invoke({
    "messages": [
        {"role": "user", "content": "I need to build a high-performance analytics dashboard. What tech stack do you recommend and what should be my first three steps?"}
    ]
})

# 6. Display the result
print("\nAgent Response:\n")
print(response["messages"][-1].content)
