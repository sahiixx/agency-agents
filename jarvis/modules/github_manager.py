"""GitHub API integration module."""

from __future__ import annotations

import requests

from config import GITHUB_TOKEN, GITHUB_USERNAME


class GitHubManager:
    """List repos, repo stats, and create issues via GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
        } if GITHUB_TOKEN else {"Accept": "application/vnd.github+json"}

    def list_repos(self, username: str = GITHUB_USERNAME) -> list[str]:
        try:
            resp = requests.get(f"{self.BASE_URL}/users/{username}/repos", headers=self.headers, timeout=15)
            if not resp.ok:
                return [f"Failed to fetch repos: {resp.status_code}"]
            return [repo.get("full_name", "unknown") for repo in resp.json()]
        except Exception as exc:
            return [f"GitHub error: {exc}"]

    def repo_status(self, owner: str, repo: str) -> str:
        try:
            resp = requests.get(f"{self.BASE_URL}/repos/{owner}/{repo}", headers=self.headers, timeout=15)
            if not resp.ok:
                return f"Could not fetch {owner}/{repo}: {resp.status_code}"
            data = resp.json()
            return (
                f"{owner}/{repo}: ⭐ {data.get('stargazers_count', 0)}, "
                f"issues {data.get('open_issues_count', 0)}, "
                f"forks {data.get('forks_count', 0)}"
            )
        except Exception as exc:
            return f"GitHub error: {exc}"

    def create_issue(self, owner: str, repo: str, title: str, body: str) -> str:
        if not GITHUB_TOKEN:
            return "Set JARVIS_GITHUB_TOKEN to create issues."
        try:
            resp = requests.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                json={"title": title, "body": body},
                timeout=15,
            )
            if not resp.ok:
                return f"Issue creation failed: {resp.status_code} {resp.text[:120]}"
            issue = resp.json()
            return f"Issue created: {issue.get('html_url', '')}"
        except Exception as exc:
            return f"GitHub error: {exc}"
