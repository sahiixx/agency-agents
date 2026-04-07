#!/usr/bin/env python3
"""
run-skill.py — Run any Agency skill as a standalone agent.

Reads a SKILL.md file, extracts the system prompt, and runs it against
the Anthropic API with streaming output. Works with skills installed
via skills.sh or directly from this repo.

Usage:
  python3 scripts/run-skill.py --skill engineering-backend-architect --task "Design a REST API"
  python3 scripts/run-skill.py --skill engineering-code-reviewer --chat
  python3 scripts/run-skill.py --skill engineering-code-reviewer --context src/api.py --task "Review"
  python3 scripts/run-skill.py --skill engineering-backend-architect --pipe testing-reality-checker --task "Design auth"
  python3 scripts/run-skill.py --skill engineering-backend-architect --tools --task "Search for best practices"
  python3 scripts/run-skill.py --skill engineering-backend-architect --output json --task "API schema"
  python3 scripts/run-skill.py --list
  echo "Review this" | python3 scripts/run-skill.py --skill engineering-code-reviewer --stdin

Requires:
  export ANTHROPIC_API_KEY="sk-ant-..."
  pip install anthropic
"""

import json
import os
import sys
import argparse
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
OUTPUTS_DIR = Path("/tmp/agency_outputs")

model = os.environ.get("AGENCY_MODEL", "claude-sonnet-4-6")

# Claude Sonnet 4.6 pricing (per million tokens)
PRICE_INPUT_PER_M = 3.00
PRICE_OUTPUT_PER_M = 15.00


# ── Skill loading ────────────────────────────────────────────────────────────

def parse_skill_md(path: Path) -> tuple[str, str, str]:
    """Extract name, description, and body from a SKILL.md file."""
    text = path.read_text()
    if not text.startswith("---"):
        return "", "", text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", "", text

    frontmatter = parts[1]
    body = parts[2].strip()

    name = ""
    description = ""
    for line in frontmatter.strip().splitlines():
        if line.startswith("name:"):
            name = line[5:].strip()
        elif line.startswith("description:"):
            description = line[12:].strip()

    return name, description, body


def find_skill(skill_name: str) -> Path | None:
    """Find a SKILL.md by skill name."""
    direct = SKILLS_DIR / skill_name / "SKILL.md"
    if direct.exists():
        return direct

    if SKILLS_DIR.exists():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                name, _, _ = parse_skill_md(skill_file)
                if name == skill_name:
                    return skill_file

    return None


def list_skills() -> list[tuple[str, str]]:
    """List all available skills."""
    skills = []
    if not SKILLS_DIR.exists():
        return skills

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            name, description, _ = parse_skill_md(skill_file)
            if name:
                skills.append((name, description))
    return skills


# ── Built-in tools (no langchain dependency) ─────────────────────────────────

def tool_web_search(query: str) -> str:
    """Search the web via DuckDuckGo instant answer."""
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "TheAgency/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())

        results = []
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
        for t in data.get("RelatedTopics", [])[:4]:
            if isinstance(t, dict) and t.get("Text"):
                results.append(f"- {t['Text']}")

        return "\n".join(results) if results else f"No instant answer found for: {query}"
    except Exception as e:
        return f"Search error: {e}"


def tool_read_file(path: str) -> str:
    """Read a file from the repo."""
    try:
        full = REPO_ROOT / path
        if not full.exists():
            return f"File not found: {path}"
        content = full.read_text(encoding="utf-8", errors="replace")
        if len(content) > 4000:
            content = content[:4000] + f"\n\n... (truncated, {len(content)} total chars)"
        return content
    except Exception as e:
        return f"Read error: {e}"


def tool_write_output(filename: str, content: str) -> str:
    """Write output to /tmp/agency_outputs/."""
    try:
        OUTPUTS_DIR.mkdir(exist_ok=True)
        safe = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe:
            safe = f"output_{datetime.now().strftime('%H%M%S')}.txt"
        path = OUTPUTS_DIR / safe
        path.write_text(content, encoding="utf-8")
        return f"Written: {path} ({len(content)} chars)"
    except Exception as e:
        return f"Write error: {e}"


def tool_get_datetime() -> str:
    """Return the current date and time in UTC."""
    return f"Current datetime: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"


TOOL_HANDLERS = {
    "web_search": lambda args: tool_web_search(args["query"]),
    "read_file": lambda args: tool_read_file(args["path"]),
    "write_output": lambda args: tool_write_output(args["filename"], args["content"]),
    "get_datetime": lambda args: tool_get_datetime(),
}

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web for current information. Returns top results as text.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "Read any file in the agency repo. Path is relative to repo root.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path relative to repo root"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_output",
        "description": "Write structured output to /tmp/agency_outputs/. Returns confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Output filename"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "get_datetime",
        "description": "Return the current date and time in UTC.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ── Cost tracking ────────────────────────────────────────────────────────────

class CostTracker:
    def __init__(self):
        self.total_input = 0
        self.total_output = 0

    def add(self, usage):
        self.total_input += getattr(usage, "input_tokens", 0)
        self.total_output += getattr(usage, "output_tokens", 0)

    @property
    def cost(self) -> float:
        return (self.total_input / 1_000_000 * PRICE_INPUT_PER_M +
                self.total_output / 1_000_000 * PRICE_OUTPUT_PER_M)

    def print_summary(self):
        print(f"Tokens: {self.total_input:,} in / {self.total_output:,} out | "
              f"Cost: ${self.cost:.4f}", file=sys.stderr)


# ── Context injection ────────────────────────────────────────────────────────

def build_context(context_files: list[str]) -> str:
    """Read files and format as context block."""
    parts = []
    for filepath in context_files:
        p = Path(filepath)
        if not p.exists():
            p = REPO_ROOT / filepath
        if not p.exists():
            print(f"Warning: context file not found: {filepath}", file=sys.stderr)
            continue
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > 100_000:
            content = content[:100_000] + "\n\n... (truncated at 100KB)"
            print(f"Warning: {filepath} truncated at 100KB", file=sys.stderr)
        parts.append(f'<file path="{filepath}">\n{content}\n</file>')

    if not parts:
        return ""
    return "<context>\n" + "\n".join(parts) + "\n</context>\n\n"


# ── Output formatting ────────────────────────────────────────────────────────

OUTPUT_INSTRUCTIONS = {
    "json": "\n\nIMPORTANT: You MUST respond with valid JSON only. No text before or after the JSON.",
    "markdown": "\n\nIMPORTANT: Format your entire response as structured Markdown with clear headers, bullet points, and code blocks.",
}


# ── Core agent runner ────────────────────────────────────────────────────────

def get_client():
    """Create an Anthropic client."""
    try:
        import anthropic
    except ImportError:
        print("Error: anthropic package not installed.", file=sys.stderr)
        print("  pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY='sk-ant-...'", file=sys.stderr)
        sys.exit(1)

    return anthropic.Anthropic(api_key=api_key)


def run_agent(client, system_prompt: str, task: str, *,
              stream: bool = True, use_tools: bool = False,
              tracker: CostTracker | None = None) -> str:
    """Run the agent. Returns the text response."""
    messages = [{"role": "user", "content": task}]

    if use_tools:
        return _run_with_tools(client, system_prompt, messages, stream=stream, tracker=tracker)

    if stream:
        text = ""
        with client.messages.stream(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
        ) as response:
            for chunk in response.text_stream:
                print(chunk, end="", flush=True)
                text += chunk
        print()
        if tracker:
            tracker.add(response.get_final_message().usage)
        return text
    else:
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
        )
        text = response.content[0].text
        if tracker:
            tracker.add(response.usage)
        return text


def _run_with_tools(client, system_prompt: str, messages: list[dict], *,
                    stream: bool = True, tracker: CostTracker | None = None,
                    max_iterations: int = 10) -> str:
    """Run with tool use loop. Returns final text response."""
    for _ in range(max_iterations):
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )
        if tracker:
            tracker.add(response.usage)

        # Collect text and tool_use blocks
        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # If there are text parts, print them
        if text_parts:
            for part in text_parts:
                print(part, end="", flush=True)

        # If no tool calls, we're done
        if not tool_uses:
            if text_parts:
                print()
            return "\n".join(text_parts)

        # Execute tools and build results
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tool_use in tool_uses:
            handler = TOOL_HANDLERS.get(tool_use.name)
            if handler:
                print(f"\n  [tool: {tool_use.name}({json.dumps(tool_use.input)[:60]})]", file=sys.stderr)
                result = handler(tool_use.input)
            else:
                result = f"Unknown tool: {tool_use.name}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    print("\nWarning: max tool iterations reached.", file=sys.stderr)
    return "\n".join(text_parts) if text_parts else ""


# ── Chat mode ────────────────────────────────────────────────────────────────

def chat_loop(client, system_prompt: str, *, use_tools: bool = False,
              tracker: CostTracker | None = None):
    """Interactive multi-turn REPL."""
    try:
        import readline  # noqa: F401 — enables input history
    except ImportError:
        pass

    messages = []
    print("Chat mode. Commands: /clear /save <file> /quit", file=sys.stderr)
    print("---", file=sys.stderr)

    while True:
        try:
            user_input = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.", file=sys.stderr)
            break

        if not user_input:
            continue

        # Handle commands
        if user_input == "/quit":
            print("Bye.", file=sys.stderr)
            break
        elif user_input == "/clear":
            messages.clear()
            print("History cleared.", file=sys.stderr)
            continue
        elif user_input.startswith("/save"):
            parts = user_input.split(maxsplit=1)
            outfile = parts[1] if len(parts) > 1 else f"chat_{datetime.now().strftime('%H%M%S')}.md"
            _save_chat(messages, outfile)
            continue

        messages.append({"role": "user", "content": user_input})

        print("\nagent> ", end="", flush=True)

        if use_tools:
            # For tool use in chat, we pass the full message history
            text = _chat_with_tools(client, system_prompt, messages, tracker=tracker)
        else:
            text = ""
            with client.messages.stream(
                model=model,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
            ) as response:
                for chunk in response.text_stream:
                    print(chunk, end="", flush=True)
                    text += chunk
            print()
            if tracker:
                tracker.add(response.get_final_message().usage)

        messages.append({"role": "assistant", "content": text})

        if tracker:
            tracker.print_summary()


def _chat_with_tools(client, system_prompt: str, messages: list[dict], *,
                     tracker: CostTracker | None = None) -> str:
    """Handle a single chat turn with tool use."""
    for _ in range(10):
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )
        if tracker:
            tracker.add(response.usage)

        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        if text_parts:
            for part in text_parts:
                print(part, end="", flush=True)

        if not tool_uses:
            if text_parts:
                print()
            return "\n".join(text_parts)

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tool_use in tool_uses:
            handler = TOOL_HANDLERS.get(tool_use.name)
            if handler:
                print(f"\n  [tool: {tool_use.name}({json.dumps(tool_use.input)[:60]})]", file=sys.stderr)
                result = handler(tool_use.input)
            else:
                result = f"Unknown tool: {tool_use.name}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    return "\n".join(text_parts) if text_parts else ""


def _save_chat(messages: list[dict], filename: str):
    """Save chat history to a file."""
    lines = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
        lines.append(f"**{role}**: {content}\n")
    Path(filename).write_text("\n".join(lines))
    print(f"Saved to {filename}", file=sys.stderr)


# ── Pipe / chain skills ─────────────────────────────────────────────────────

def run_pipe(client, skills: list[tuple[str, str]], task: str, *,
             use_tools: bool = False, tracker: CostTracker | None = None,
             stream_final: bool = True) -> str:
    """Chain multiple skills. Output of each becomes input of the next."""
    current_output = task

    for i, (name, system_prompt) in enumerate(skills):
        is_last = (i == len(skills) - 1)
        print(f"  [{i+1}/{len(skills)}] Running: {name}", file=sys.stderr)

        if i > 0:
            current_output = (
                f"Previous agent output:\n\n{current_output}\n\n"
                f"Your task: continue from here and apply your expertise."
            )

        if is_last and stream_final:
            current_output = run_agent(
                client, system_prompt, current_output,
                stream=True, use_tools=use_tools, tracker=tracker,
            )
        else:
            current_output = run_agent(
                client, system_prompt, current_output,
                stream=False, use_tools=use_tools, tracker=tracker,
            )

    return current_output


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    global model

    parser = argparse.ArgumentParser(
        description="Run any Agency skill as a standalone agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  %(prog)s --skill engineering-backend-architect --task 'Design a REST API'\n"
               "  %(prog)s --skill engineering-code-reviewer --chat\n"
               "  %(prog)s --skill engineering-code-reviewer --context src/api.py --task 'Review'\n"
               "  %(prog)s --skill engineering-backend-architect --pipe testing-reality-checker --task 'Auth API'\n"
               "  %(prog)s --skill engineering-backend-architect --tools --task 'Search best practices'\n"
               "  %(prog)s --list\n",
    )
    parser.add_argument("--skill", "-s", help="Skill name (e.g. engineering-backend-architect)")
    parser.add_argument("--task", "-t", help="Task/prompt to send to the agent")
    parser.add_argument("--stdin", action="store_true", help="Read task from stdin")
    parser.add_argument("--list", "-l", action="store_true", help="List all available skills")
    parser.add_argument("--chat", action="store_true", help="Interactive multi-turn chat mode")
    parser.add_argument("--tools", action="store_true", help="Enable tool use (web search, file read, etc.)")
    parser.add_argument("--context", nargs="+", metavar="FILE", help="Prepend file contents to task")
    parser.add_argument("--pipe", nargs="+", metavar="SKILL", help="Chain skills (output -> input)")
    parser.add_argument("--output", choices=["text", "json", "markdown"], default="text", help="Output format")
    parser.add_argument("--cost", action="store_true", help="Show token usage and cost")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming output")
    parser.add_argument("--model", "-m", help=f"Model to use (default: {model})")
    parser.add_argument("--skill-file", help="Path to a SKILL.md file directly")

    args = parser.parse_args()

    if args.model:
        model = args.model

    # List mode
    if args.list:
        skills = list_skills()
        if not skills:
            print("No skills found. Run: ./scripts/convert.sh --tool skillssh")
            sys.exit(1)
        print(f"Available skills ({len(skills)}):\n")
        current_domain = ""
        for name, desc in skills:
            domain = name.split("-")[0] if "-" in name else "other"
            if domain != current_domain:
                current_domain = domain
                print(f"\n  [{domain}]")
            short_desc = desc[:80] + "..." if len(desc) > 80 else desc
            print(f"    {name:<50} {short_desc}")
        print()
        return

    # Require skill
    if not args.skill and not args.skill_file:
        parser.error("--skill or --skill-file is required (or use --list)")

    # Load primary skill
    if args.skill_file:
        skill_path = Path(args.skill_file)
        if not skill_path.exists():
            print(f"Error: file not found: {args.skill_file}", file=sys.stderr)
            sys.exit(1)
    else:
        skill_path = find_skill(args.skill)
        if not skill_path:
            print(f"Error: skill '{args.skill}' not found.", file=sys.stderr)
            print(f"  Run: python3 {sys.argv[0]} --list", file=sys.stderr)
            sys.exit(1)

    name, description, body = parse_skill_md(skill_path)
    system_prompt = body

    # Apply output format instruction
    if args.output in OUTPUT_INSTRUCTIONS:
        system_prompt += OUTPUT_INSTRUCTIONS[args.output]

    # Setup
    tracker = CostTracker() if args.cost else None
    client = get_client()

    print(f"Agent: {name}", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)
    if args.tools:
        print(f"Tools: web_search, read_file, write_output, get_datetime", file=sys.stderr)
    print(f"---", file=sys.stderr)

    # Chat mode
    if args.chat:
        chat_loop(client, system_prompt, use_tools=args.tools, tracker=tracker)
        if tracker:
            print("--- Session totals ---", file=sys.stderr)
            tracker.print_summary()
        return

    # Get task
    if args.stdin:
        task = sys.stdin.read().strip()
    elif args.task:
        task = args.task
    else:
        parser.error("--task, --stdin, or --chat is required")

    if not task:
        print("Error: empty task.", file=sys.stderr)
        sys.exit(1)

    # Prepend context files
    if args.context:
        context_block = build_context(args.context)
        task = context_block + task

    # Pipe mode
    if args.pipe:
        skill_chain = [(name, system_prompt)]
        for pipe_skill_name in args.pipe:
            pipe_path = find_skill(pipe_skill_name)
            if not pipe_path:
                print(f"Error: piped skill '{pipe_skill_name}' not found.", file=sys.stderr)
                sys.exit(1)
            p_name, _, p_body = parse_skill_md(pipe_path)
            if args.output in OUTPUT_INSTRUCTIONS:
                p_body += OUTPUT_INSTRUCTIONS[args.output]
            skill_chain.append((p_name, p_body))

        output = run_pipe(
            client, skill_chain, task,
            use_tools=args.tools, tracker=tracker,
            stream_final=not args.no_stream,
        )
    else:
        # Single skill run
        output = run_agent(
            client, system_prompt, task,
            stream=not args.no_stream, use_tools=args.tools, tracker=tracker,
        )

    # JSON validation
    if args.output == "json" and not args.no_stream:
        try:
            parsed = json.loads(output)
            # Re-print formatted (streaming already printed raw)
        except json.JSONDecodeError:
            print("\nWarning: response is not valid JSON.", file=sys.stderr)
    elif args.output == "json" and args.no_stream:
        try:
            parsed = json.loads(output)
            print(json.dumps(parsed, indent=2))
        except json.JSONDecodeError:
            print(output)
            print("\nWarning: response is not valid JSON.", file=sys.stderr)
    elif args.no_stream and not args.pipe:
        print(output)

    if tracker:
        tracker.print_summary()


if __name__ == "__main__":
    main()
