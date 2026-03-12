import os
import random
import subprocess
import sys
import datetime

# Add Deep Agents to PYTHONPATH
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(REPO_DIR, "deepagents/libs/deepagents"))

def get_all_agents():
    """Recursively finds all agent personality files in the repository."""
    agents = []
    excluded_dirs = {'.git', 'node_modules', 'deepagents', 'integrations', 'scaffold', 'tests', 'scripts'}
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for file in files:
            if file.endswith('.md') and file not in ['README.md', 'CONTRIBUTING.md', 'LICENSE.md', 'AGENTS.md', 'README_DEEPAGENTS.md']:
                agents.append(os.path.join(root, file))
    return agents

def run_evolution(agent_path):
    """Runs the Sovereign Ecosystem evolution cycle on a specific agent."""
    print(f"[{datetime.datetime.now()}] Evolving agent: {agent_path}")
    try:
        subprocess.run([sys.executable, "sovereign_ecosystem.py", "--agent", agent_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during evolution: {e}")
        return False

def run_benchmarks():
    """Runs the Agent Test Suite to ensure perfection after evolution."""
    print(f"[{datetime.datetime.now()}] Running benchmarks...")
    try:
        subprocess.run([sys.executable, "tests/agent_tests.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Benchmarks failed: {e}")
        return False

def commit_changes(agent_path):
    """Commits the evolution changes to GitHub."""
    agent_name = os.path.basename(agent_path)
    print(f"[{datetime.datetime.now()}] Committing improvements for {agent_name}...")
    try:
        subprocess.run(["git", "add", agent_path], check=True)
        subprocess.run(["git", "commit", "-m", f"Eternal Evolution: Optimized and benchmarked {agent_name}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("GitHub synchronization successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error during git operations: {e}")

def main():
    agents = get_all_agents()
    if not agents:
        print("No agents found to evolve.")
        return

    # Select a random agent to evolve
    target_agent = random.choice(agents)
    
    if run_evolution(target_agent):
        if run_benchmarks():
            commit_changes(target_agent)
            print(f"🏁 Evolution cycle for {target_agent} completed perfectly.")
        else:
            print("⚠️ Evolution cycle failed benchmarks. Reverting changes...")
            subprocess.run(["git", "checkout", target_agent], check=True)
    else:
        print("❌ Evolution cycle failed.")

if __name__ == "__main__":
    main()
