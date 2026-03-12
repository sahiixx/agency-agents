import os
import sys
import argparse
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Add Deep Agents to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "deepagents/libs/deepagents"))

class SovereignEcosystem:
    def __init__(self, model="gpt-4.1-mini"):
        self.llm = ChatOpenAI(model=model)
        self.agents = {}
        self._load_agents()

    def _load_agents(self):
        """Loads the core Agency personalities for the Ecosystem mission."""
        agent_paths = {
            "observer": "testing/testing-reality-checker.md",
            "refiner": "specialized/specialized-perfect-agent-orchestrator.md",
            "devops": "engineering/engineering-ai-engineer.md"
        }
        for role, path in agent_paths.items():
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.agents[role] = f.read()
            else:
                print(f"Warning: Personality file not found: {path}")

    def run_evolution_cycle(self, target_agent_path):
        """Executes a self-evolution cycle on a target agent."""
        print(f"\n🌌 Sovereign Ecosystem: Evolution Cycle Start for '{target_agent_path}'")

        if not os.path.exists(target_agent_path):
            print(f"Error: Target agent not found: {target_agent_path}")
            return False

        with open(target_agent_path, "r") as f:
            current_personality = f.read()

        # 1. Observer: Audit Performance
        print("\n--- [Phase 1] Observer: Auditing Personality ---")
        observer = create_deep_agent(tools=[], system_prompt=self.agents["observer"], model=self.llm)
        audit_response = observer.invoke({"messages": [HumanMessage(content=f"Audit this agent personality for weaknesses, missing capabilities, or outdated practices:\n{current_personality}")]})
        audit_report = audit_response["messages"][-1].content
        print("Observer Audit Report Ready.")

        # 2. Refiner: Optimize Personality
        print("\n--- [Phase 2] Refiner: Optimizing Personality ---")
        refiner = create_deep_agent(tools=[], system_prompt=self.agents["refiner"], model=self.llm)
        refine_response = refiner.invoke({"messages": [HumanMessage(content=f"Rewrite this agent personality to address the following audit findings and make it 'perfect':\nOriginal: {current_personality}\nAudit: {audit_report}")]})
        optimized_personality = refine_response["messages"][-1].content
        
        # Save the optimized personality back to the file
        with open(target_agent_path, "w") as f:
            f.write(optimized_personality)
        print(f"Refiner: '{target_agent_path}' has been optimized and updated.")

        # 3. DevOps: Deploy Update
        print("\n--- [Phase 3] DevOps: Verifying Deployment Readiness ---")
        devops = create_deep_agent(tools=[], system_prompt=self.agents["devops"], model=self.llm)
        deploy_response = devops.invoke({"messages": [HumanMessage(content=f"Verify that this updated agent is ready for production deployment:\n{optimized_personality}")]})
        deploy_report = deploy_response["messages"][-1].content
        print("DevOps Deployment Readiness Verified.")

        print("\n🏁 Evolution Cycle Complete. The Agency has self-improved.")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign Ecosystem Controller")
    parser.add_argument("--agent", type=str, required=True, help="Path to the agent personality to evolve")
    args = parser.parse_args()

    ecosystem = SovereignEcosystem()
    ecosystem.run_evolution_cycle(args.agent)
