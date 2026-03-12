import os
import sys
import argparse
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Add Deep Agents to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "deepagents/libs/deepagents"))

class AgencySwarm:
    def __init__(self, model="gpt-4.1-mini"):
        self.llm = ChatOpenAI(model=model)
        self.agents = {}
        self._load_agents()

    def _load_agents(self):
        """Loads the core Agency personalities for the swarm."""
        agent_paths = {
            "pm": "project-management/project-manager-senior.md",
            "frontend": "engineering/engineering-frontend-developer.md",
            "qa": "testing/testing-reality-checker.md"
        }
        for role, path in agent_paths.items():
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.agents[role] = f.read()
            else:
                print(f"Warning: Personality file not found: {path}")

    def run_mission(self, mission_goal):
        """Executes a full multi-agent mission."""
        print(f"\n🚀 Mission Start: {mission_goal}")

        # 1. Project Manager: Plan and Scaffold
        print("\n--- [Phase 1] Project Manager Planning ---")
        pm_agent = create_deep_agent(tools=[], system_prompt=self.agents["pm"], model=self.llm)
        plan_response = pm_agent.invoke({"messages": [HumanMessage(content=f"Create a detailed execution plan for: {mission_goal}")]})
        plan = plan_response["messages"][-1].content
        print(f"PM Plan:\n{plan[:500]}...")

        # 2. Frontend Developer: Implementation
        print("\n--- [Phase 2] Frontend Developer Implementation ---")
        dev_agent = create_deep_agent(tools=[], system_prompt=self.agents["frontend"], model=self.llm)
        dev_response = dev_agent.invoke({"messages": [HumanMessage(content=f"Implement the UI based on this plan:\n{plan}")]})
        code = dev_response["messages"][-1].content
        print(f"Frontend Implementation:\n{code[:500]}...")

        # 3. QA Tester: Verification
        print("\n--- [Phase 3] QA Reality Check ---")
        qa_agent = create_deep_agent(tools=[], system_prompt=self.agents["qa"], model=self.llm)
        qa_response = qa_agent.invoke({"messages": [HumanMessage(content=f"Audit this implementation for errors and best practices:\n{code}")]})
        audit = qa_response["messages"][-1].content
        print(f"QA Audit:\n{audit[:500]}...")

        print("\n🏁 Mission Complete: Total Dominance Achieved.")
        return {"plan": plan, "code": code, "audit": audit}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agency Swarm Orchestrator")
    parser.add_argument("--mission", type=str, required=True, help="The mission goal for the swarm")
    args = parser.parse_args()

    swarm = AgencySwarm()
    swarm.run_mission(args.mission)
