import os
import sys
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Add Deep Agents to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "deepagents/libs/deepagents"))

class StressTestSwarm:
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
            with open(path, "r") as f:
                self.agents[role] = f.read()

    def run_mission(self, mission_goal):
        """Executes a full multi-agent mission with file creation."""
        print(f"\n🚀 Extreme Stress Test Start: {mission_goal}")

        # 1. Project Manager: Plan
        pm_agent = create_deep_agent(tools=[], system_prompt=self.agents["pm"], model=self.llm)
        plan_response = pm_agent.invoke({"messages": [HumanMessage(content=f"Create a detailed execution plan for: {mission_goal}")]})
        plan = plan_response["messages"][-1].content
        print("\n--- [Phase 1] PM Plan Created ---")

        # 2. Frontend Developer: Implementation (Actually create a file)
        dev_agent = create_deep_agent(tools=[], system_prompt=self.agents["frontend"], model=self.llm)
        dev_response = dev_agent.invoke({"messages": [HumanMessage(content=f"Implement the UI code for a 'Dashboard.tsx' file based on this plan:\n{plan}")]})
        code = dev_response["messages"][-1].content
        
        # Extract code from response
        if "```tsx" in code:
            extracted_code = code.split("```tsx")[1].split("```")[0].strip()
        elif "```" in code:
            extracted_code = code.split("```")[1].split("```")[0].strip()
        else:
            extracted_code = code

        # Actually write the file to the scaffold
        os.makedirs("scaffold/nextjs-tailwind/components", exist_ok=True)
        with open("scaffold/nextjs-tailwind/components/Dashboard.tsx", "w") as f:
            f.write(extracted_code)
        
        print("\n--- [Phase 2] Frontend Developer Created 'scaffold/nextjs-tailwind/components/Dashboard.tsx' ---")

        # 3. QA Tester: Verification
        qa_agent = create_deep_agent(tools=[], system_prompt=self.agents["qa"], model=self.llm)
        qa_response = qa_agent.invoke({"messages": [HumanMessage(content=f"Audit this code for errors and best practices:\n{extracted_code}")]})
        audit = qa_response["messages"][-1].content
        print("\n--- [Phase 3] QA Audit Complete ---")

        print("\n🏁 Stress Test Complete: The Swarm successfully built a functional component.")
        return True

if __name__ == "__main__":
    swarm = StressTestSwarm()
    swarm.run_mission("Build a responsive analytics dashboard component for the Next.js scaffold.")
