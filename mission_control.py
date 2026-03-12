import os
import argparse
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

def list_agents():
    """Lists all available agent personalities."""
    agents = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".md") and ("engineering" in root or "design" in root or "marketing" in root or "specialized" in root):
                agents.append(os.path.join(root, file))
    return agents

def launch_agent(agent_path, query):
    """Launches a specific agent with a query."""
    with open(agent_path, "r") as f:
        system_prompt = f.read()
    
    llm = ChatOpenAI(model="gpt-4.1-mini")
    agent = create_deep_agent(tools=[], system_prompt=system_prompt, model=llm)
    
    print(f"\n--- Launching Agent: {os.path.basename(agent_path)} ---")
    response = agent.invoke({"messages": [{"role": "user", "content": query}]})
    print("\nResponse:\n")
    print(response["messages"][-1].content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Agency: Mission Control CLI")
    parser.add_argument("--list", action="store_true", help="List all available agents")
    parser.add_argument("--agent", type=str, help="Path to the agent personality file")
    parser.add_argument("--query", type=str, help="The task or query for the agent")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available Agents:")
        for agent in list_agents():
            print(f"  - {agent}")
    elif args.agent and args.query:
        launch_agent(args.agent, args.query)
    else:
        parser.print_help()
