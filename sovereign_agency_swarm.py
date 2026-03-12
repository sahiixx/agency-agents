import os
import sys
import argparse
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Add Deep Agents to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "deepagents/libs/deepagents"))

class SovereignSwarm:
    def __init__(self, model="gpt-4.1-mini"):
        self.llm = ChatOpenAI(model=model)
        self.agents = {}
        self._load_agents()

    def _load_agents(self):
        """Loads the core Agency personalities for the Sovereign mission."""
        agent_paths = {
            "pm": "project-management/project-manager-senior.md",
            "backend": "engineering/engineering-backend-architect.md",
            "frontend": "engineering/engineering-frontend-developer.md",
            "qa": "testing/testing-reality-checker.md",
            "growth": "marketing/marketing-growth-hacker.md",
            "ai": "engineering/engineering-ai-engineer.md"
        }
        for role, path in agent_paths.items():
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.agents[role] = f.read()
            else:
                print(f"Warning: Personality file not found: {path}")

    def run_mission(self, mission_goal):
        """Executes a 6-agent full-stack Sovereign mission."""
        print(f"\n👑 Sovereign Agency Mission Start: {mission_goal}")

        # 1. Project Manager: Full-Stack Architecture
        print("\n--- [Phase 1] PM Full-Stack Architecture ---")
        pm_agent = create_deep_agent(tools=[], system_prompt=self.agents["pm"], model=self.llm)
        plan_response = pm_agent.invoke({"messages": [HumanMessage(content=f"Create a production-ready full-stack architecture for: {mission_goal}. Include DB schema and API route definitions.")]})
        plan = plan_response["messages"][-1].content
        print(f"PM Full-Stack Plan Ready.")

        # 2. Backend Architect: API & DB Implementation
        print("\n--- [Phase 2] Backend Architect API Design ---")
        backend_agent = create_deep_agent(tools=[], system_prompt=self.agents["backend"], model=self.llm)
        backend_response = backend_agent.invoke({"messages": [HumanMessage(content=f"Design the Prisma schema and API routes for this plan:\n{plan}")]})
        backend_code = backend_response["messages"][-1].content
        print(f"Backend API & DB Schema Ready.")

        # 3. AI Engineer: Agent Integration Logic
        print("\n--- [Phase 3] AI Engineer Agent Logic ---")
        ai_agent = create_deep_agent(tools=[], system_prompt=self.agents["ai"], model=self.llm)
        ai_response = ai_agent.invoke({"messages": [HumanMessage(content=f"Implement the core AI agent orchestration logic for this platform based on the plan:\n{plan}")]})
        ai_logic = ai_response["messages"][-1].content
        print(f"AI Agent Logic Ready.")

        # 4. Frontend Developer: Dashboard Implementation
        print("\n--- [Phase 4] Frontend Developer UI Implementation ---")
        dev_agent = create_deep_agent(tools=[], system_prompt=self.agents["frontend"], model=self.llm)
        dev_response = dev_agent.invoke({"messages": [HumanMessage(content=f"Implement the full Next.js dashboard UI using this plan and backend logic:\nPlan: {plan}\nBackend: {backend_code}")]})
        frontend_code = dev_response["messages"][-1].content
        print(f"Frontend Dashboard UI Ready.")

        # Save all results to the scaffold
        os.makedirs("scaffold/sovereign-platform/api", exist_ok=True)
        os.makedirs("scaffold/sovereign-platform/components", exist_ok=True)
        os.makedirs("scaffold/sovereign-platform/ai", exist_ok=True)
        
        with open("scaffold/sovereign-platform/schema.prisma", "w") as f:
            f.write(backend_code)
        with open("scaffold/sovereign-platform/ai/orchestrator.ts", "w") as f:
            f.write(ai_logic)
        with open("scaffold/sovereign-platform/components/Dashboard.tsx", "w") as f:
            f.write(frontend_code)
            
        print(f"All full-stack components saved to 'scaffold/sovereign-platform/'.")

        # 5. QA Tester: Verification
        print("\n--- [Phase 5] QA Reality Check ---")
        qa_agent = create_deep_agent(tools=[], system_prompt=self.agents["qa"], model=self.llm)
        qa_response = qa_agent.invoke({"messages": [HumanMessage(content=f"Audit this full-stack platform for security, performance, and reliability:\nFrontend: {frontend_code}\nBackend: {backend_code}")]})
        audit = qa_response["messages"][-1].content
        print(f"QA Audit Complete.")

        print("\n🏁 Sovereign Agency Mission Complete. Total Dominance Achieved.")
        return True

if __name__ == "__main__":
    swarm = SovereignSwarm()
    swarm.run_mission("Build a production-ready AI Agent Management Platform with multi-agent swarming, live monitoring, and automated deployment.")
