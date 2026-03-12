import os
import sys
import argparse
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Add Deep Agents to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "deepagents/libs/deepagents"))

class SaasSwarm:
    def __init__(self, model="gpt-4.1-mini"):
        self.llm = ChatOpenAI(model=model)
        self.agents = {}
        self._load_agents()

    def _load_agents(self):
        """Loads the core Agency personalities for the SaaS mission."""
        agent_paths = {
            "pm": "project-management/project-manager-senior.md",
            "frontend": "engineering/engineering-frontend-developer.md",
            "qa": "testing/testing-reality-checker.md",
            "copy": "marketing/marketing-growth-hacker.md"
        }
        for role, path in agent_paths.items():
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.agents[role] = f.read()
            else:
                print(f"Warning: Personality file not found: {path}")

    def run_mission(self, mission_goal):
        """Executes a 4-agent SaaS dominance mission."""
        print(f"\n🚀 SaaS Dominance Mission Start: {mission_goal}")

        # 1. Project Manager: Plan
        print("\n--- [Phase 1] PM Strategic Planning ---")
        pm_agent = create_deep_agent(tools=[], system_prompt=self.agents["pm"], model=self.llm)
        plan_response = pm_agent.invoke({"messages": [HumanMessage(content=f"Create a high-performance SaaS architecture plan for: {mission_goal}")]})
        plan = plan_response["messages"][-1].content
        print(f"PM Plan Ready.")

        # 2. Copywriter: Marketing Content
        print("\n--- [Phase 2] Copywriter Content Generation ---")
        copy_agent = create_deep_agent(tools=[], system_prompt=self.agents["copy"], model=self.llm)
        copy_response = copy_agent.invoke({"messages": [HumanMessage(content=f"Write high-conversion marketing copy for this SaaS based on the plan:\n{plan}")]})
        copy_content = copy_response["messages"][-1].content
        print(f"Copywriter Content Ready.")

        # 3. Frontend Developer: Implementation
        print("\n--- [Phase 3] Frontend Developer Implementation ---")
        dev_agent = create_deep_agent(tools=[], system_prompt=self.agents["frontend"], model=self.llm)
        dev_response = dev_agent.invoke({"messages": [HumanMessage(content=f"Implement the UI for the SaaS landing page using this plan and copy:\nPlan: {plan}\nCopy: {copy_content}")]})
        code = dev_response["messages"][-1].content
        
        # Extract and save code
        os.makedirs("scaffold/nextjs-tailwind/pages", exist_ok=True)
        with open("scaffold/nextjs-tailwind/pages/saas-landing.tsx", "w") as f:
            f.write(code)
        print(f"Frontend Implementation Saved to 'scaffold/nextjs-tailwind/pages/saas-landing.tsx'.")

        # 4. QA Tester: Verification
        print("\n--- [Phase 4] QA Reality Check ---")
        qa_agent = create_deep_agent(tools=[], system_prompt=self.agents["qa"], model=self.llm)
        qa_response = qa_agent.invoke({"messages": [HumanMessage(content=f"Audit this SaaS landing page for SEO, accessibility, and conversion optimization:\n{code}")]})
        audit = qa_response["messages"][-1].content
        print(f"QA Audit Complete.")

        print("\n🏁 SaaS Dominance Mission Complete.")
        return {"plan": plan, "copy": copy_content, "code": code, "audit": audit}

if __name__ == "__main__":
    swarm = SaasSwarm()
    swarm.run_mission("Build a high-conversion SaaS Landing Page for an AI Agent Agency.")
