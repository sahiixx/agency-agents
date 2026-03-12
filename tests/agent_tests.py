import os
import unittest
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

class TestAgentPersonalities(unittest.TestCase):
    def setUp(self):
        self.llm = ChatOpenAI(model="gpt-4.1-mini")

    def test_frontend_developer_identity(self):
        """Verify the Frontend Developer agent knows its identity and tools."""
        with open("engineering/engineering-frontend-developer.md", "r") as f:
            system_prompt = f.read()
        
        agent = create_deep_agent(tools=[], system_prompt=system_prompt, model=self.llm)
        response = agent.invoke({"messages": [{"role": "user", "content": "Who are you and what is your core mission?"}]})
        content = response["messages"][-1].content.lower()
        
        self.assertIn("frontend", content)
        self.assertIn("developer", content)

    def test_backend_architect_identity(self):
        """Verify the Backend Architect agent knows its identity."""
        with open("engineering/engineering-backend-architect.md", "r") as f:
            system_prompt = f.read()
        
        agent = create_deep_agent(tools=[], system_prompt=system_prompt, model=self.llm)
        response = agent.invoke({"messages": [{"role": "user", "content": "What is your specialty?"}]})
        content = response["messages"][-1].content.lower()
        
        self.assertIn("backend", content)
        self.assertIn("architect", content)

if __name__ == "__main__":
    unittest.main()
