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
    """
    Parse a SKILL.md file and return its declared name, description, and the remaining body.
    
    If the file does not start with a YAML frontmatter marker (`---`) or the frontmatter cannot be split, the entire file is treated as the body and empty strings are returned for `name` and `description`. When frontmatter is present, `name:` and `description:` lines are extracted (trimmed) from the frontmatter; the body is the remainder after the second `---`, trimmed of surrounding whitespace.
    
    Parameters:
        path (Path): Path to the SKILL.md file.
    
    Returns:
        tuple[str, str, str]: A tuple of `(name, description, body)`. `name` and `description` are empty strings if not present; `body` is the file text (or the part after frontmatter).
    """
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
    """
    Return a list of discovered skills with their descriptions.
    
    Returns:
        list[tuple[str, str]]: A list of (name, description) pairs for each skill that has a non-empty parsed name.
    """
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
    """
    Retrieve a short DuckDuckGo instant-answer summary and up to four related-topic lines for a query.
    
    Parameters:
        query (str): The search query to look up.
    
    Returns:
        str: A text block containing a "Summary: ..." line if an instant answer exists followed by up to four "- ..." related-topic lines; if no instant answer is available returns "No instant answer found for: <query>"; on failures returns "Search error: <exception>".
    """
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
    """
    Read a file located under the repository root and return its text.
    
    Parameters:
        path (str): Path to the file, interpreted relative to the repository root.
    
    Returns:
        str: The file contents decoded as UTF-8 with replacement for invalid bytes. If the file is larger than 4000 characters the returned string is truncated with a trailing note indicating the original total length. If the file does not exist, returns a string of the form "File not found: <path>". On I/O or other errors, returns a string beginning with "Read error: " followed by the exception text.
    """
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
    """
    Write the given content to a file under /tmp/agency_outputs/, returning a confirmation or an error message.
    
    Parameters:
        filename (str): Desired filename; will be sanitized to contain only alphanumeric characters and the characters . _ - . If the sanitized result is empty, a timestamped fallback name is used.
        content (str): Text to write into the file (UTF-8).
    
    Returns:
        str: A confirmation string containing the written path and character count on success, or an error message starting with "Write error:" on failure.
    """
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
    """
    Get the current UTC date and time formatted as "YYYY-MM-DD HH:MM:SS".
    
    Returns:
        formatted (str): A string prefixed with "Current datetime: " and suffixed with " UTC", e.g. "Current datetime: 2026-04-07 12:34:56 UTC".
    """
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
        """
        Initialize a CostTracker with zeroed token counters.
        
        Attributes:
            total_input (int): Cumulative number of input tokens seen.
            total_output (int): Cumulative number of output tokens produced.
        """
        self.total_input = 0
        self.total_output = 0

    def add(self, usage):
        """
        Add token usage counts from a response usage object to the tracker totals.
        
        Parameters:
            usage: An object (e.g., API response usage) that may have `input_tokens` and/or `output_tokens` attributes; their integer values are added to the tracker's totals. Missing attributes are treated as zero.
        """
        self.total_input += getattr(usage, "input_tokens", 0)
        self.total_output += getattr(usage, "output_tokens", 0)

    @property
    def cost(self) -> float:
        """
        Calculate the estimated USD cost based on accumulated input and output token counts.
        
        Returns:
            float: Estimated cost in USD computed as (input tokens × input price per million + output tokens × output price per million) divided by 1,000,000.
        """
        return (self.total_input / 1_000_000 * PRICE_INPUT_PER_M +
                self.total_output / 1_000_000 * PRICE_OUTPUT_PER_M)

    def print_summary(self):
        """
        Prints a concise token and cost summary to standard error.
        
        Outputs the total input and output token counts and the estimated USD cost formatted in a single line to stderr.
        """
        print(f"Tokens: {self.total_input:,} in / {self.total_output:,} out | "
              f"Cost: ${self.cost:.4f}", file=sys.stderr)


# ── Context injection ────────────────────────────────────────────────────────

def build_context(context_files: list[str]) -> str:
    """
    Build an XML-like `<context>` block from a list of file paths.
    
    Reads each path (falling back to the repository root if the path is not found as given), truncates files larger than 100 KB with a warning, and wraps each file's contents in a `<file path="...">...</file>` element. If no files are successfully read, returns an empty string.
    
    Parameters:
        context_files (list[str]): File paths to include in the context block.
    
    Returns:
        context_block (str): A string containing the `<context>` element with one `<file>` child per successfully read file, or an empty string if none were read.
    """
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
    """
              Send a task to the model using the provided system prompt and return the assistant's text response.
              
              If `use_tools` is true, runs the tool-enabled interaction loop. If `stream` is true, streamed text chunks are printed to stdout as they arrive and the full concatenated text is returned. When a `tracker` is provided and the client response includes usage data, the tracker will be updated with that usage.
              
              Parameters:
                  system_prompt (str): The system-level prompt or skill body to use for the call.
                  task (str): The user's task or input message content.
                  stream (bool): If true, stream response chunks from the model and print them as received.
                  use_tools (bool): If true, enable tool invocation handling and iterate with tool calls.
                  tracker (CostTracker | None): Optional cost tracker to accumulate token usage from responses.
              
              Returns:
                  str: The assistant's full text response.
              """
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
    """
                    Run a tool-enabled message loop until the assistant stops requesting tools or the iteration limit is reached.
                    
                    Sends the current message history to the model with the configured tool definitions, prints any assistant text to stdout as it is returned, executes requested tools via the registered handlers, and appends the assistant responses and tool result blocks back into the provided `messages` list (mutating it). Updates `tracker` with usage information when available. If the loop reaches `max_iterations` without completion, a warning is printed to stderr.
                    
                    Parameters:
                        client: The Anthropic client used to create messages.
                        system_prompt (str): System prompt to include on each model call.
                        messages (list[dict]): Conversation history as a list of message dicts; this list is mutated with assistant and tool-result/user entries.
                        stream (bool): Unused in the current implementation but accepted for API compatibility.
                        tracker (CostTracker | None): Optional cost tracker to accumulate model usage.
                        max_iterations (int): Maximum number of tool-invocation cycles to perform.
                    
                    Returns:
                        str: The concatenated assistant text produced during the final model response (joined with newline characters), or an empty string if no text was produced.
                    """
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
    """
              Start an interactive multi-turn chat session with the agent.
              
              Each user input is appended to a running message history and sent to the model; assistant responses are printed and appended to the history. Supports optional tool-enabled multi-step tool execution per turn and optional cost tracking.
              
              Parameters:
                  client: Anthropic-compatible client used to send and stream messages.
                  system_prompt (str): The system prompt / skill instructions prepended to each request.
                  use_tools (bool): If True, enable the tool-execution loop for turns (uses internal tool protocol).
                  tracker (CostTracker | None): Optional tracker to accumulate token usage and print cost summaries.
              """
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
    """
                     Run a single chat turn that permits the model to request and receive tool results.
                     
                     Processes the provided conversation messages with the given system prompt, allowing the model to issue tool calls; executes any requested tool handlers and feeds their results back into the conversation until the model returns text without further tool requests or an iteration limit is reached. Text parts produced by the model are printed to stdout as they arrive.
                     
                     Parameters:
                         system_prompt (str): The system prompt to include for this turn.
                         messages (list[dict]): Conversation history as a list of message dicts (roles and contents).
                         tracker (CostTracker | None): Optional cost tracker to accumulate model usage.
                     
                     Returns:
                         str: The assistant's concatenated text response, or an empty string if no text was produced.
                     """
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
    """
    Write a simple transcript of `messages` to `filename` and print the saved path to stderr.
    
    Each message becomes a line in the file formatted as "**<role>**: <content>". Non-string `content` values are converted with `str()` before writing.
    
    Parameters:
        messages (list[dict]): Sequence of message objects with keys `"role"` and `"content"`.
        filename (str): Path to the output file to write.
    """
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
    """
             Run a sequence of skills, feeding each skill's output as the next skill's input.
             
             Each entry in `skills` should be a (name, system_prompt) pair; the skill's system prompt is used to run that step. The initial `task` is sent to the first skill. For each subsequent skill, the previous step's output is prepended to the new task using a "Previous agent output" wrapper and an instruction to continue from there. Progress for each step is printed to stderr.
             
             Parameters:
                 client: Anthropic API client (omitted from param docs by convention).
                 skills (list[tuple[str, str]]): Ordered list of skills as (name, system_prompt).
                 task (str): Initial task sent to the first skill.
                 use_tools (bool): If true, enables tool use when running each skill.
                 tracker (CostTracker | None): Optional cost tracker to accumulate usage across steps.
                 stream_final (bool): If true, stream the final skill's output; intermediate steps are always run non-streaming.
             
             Returns:
                 str: The final skill's output after the chain completes.
             """
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
    """
    Entry point for the CLI that runs an Agency skill as a standalone agent.
    
    Parses command-line arguments, loads the requested skill, and executes one of:
    - a single skill run,
    - an interactive chat session,
    - or a chained pipeline of skills.
    
    Supports reading the task from --task or --stdin, optional context file injection via --context,
    tool-enabled runs (--tools), output format hints (--output), streaming control (--no-stream),
    and optional token cost tracking (--cost). Prints status and results to stdout/stderr and
    exits with a nonzero status for fatal errors (missing skill/file, empty task, etc.).
    """
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
