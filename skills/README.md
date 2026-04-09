# The Agency — skills.sh Skills

151 specialized AI agent personas, installable as skills via [skills.sh](https://skills.sh).

## Install

```bash
# Install all skills
npx skills add sahiixx/agency-agents

# Install a specific skill
npx skills add sahiixx/agency-agents --skill engineering-backend-architect
```

## Run Standalone

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Single task
python3 scripts/run-skill.py --skill engineering-backend-architect --task "Design a REST API"

# Interactive chat
python3 scripts/run-skill.py --skill engineering-code-reviewer --chat

# With tool use (web search, file read)
python3 scripts/run-skill.py --skill engineering-ai-engineer --tools --task "Search for RAG best practices"

# Feed files as context
python3 scripts/run-skill.py --skill engineering-code-reviewer --context src/api.py --task "Review this code"

# Chain skills (output of one → input of next)
python3 scripts/run-skill.py --skill engineering-backend-architect --pipe testing-reality-checker --task "Design auth API"

# Structured output
python3 scripts/run-skill.py --skill engineering-backend-architect --output json --task "API schema"

# Cost tracking
python3 scripts/run-skill.py --skill engineering-backend-architect --cost --task "Design a REST API"

# List all skills
python3 scripts/run-skill.py --list
```

## Categories

| Domain | Count | Examples |
|--------|-------|---------|
| Engineering | 21 | backend-architect, frontend-developer, security-engineer, devops-automator |
| Marketing | 19 | growth-hacker, seo-specialist, tiktok-strategist, content-creator |
| Specialized | 18 | claude-reasoning-core, mcp-builder, compliance-auditor |
| Real Estate | 9 | lead-qualification, property-matching, deal-negotiation |
| Design | 8 | ux-architect, ui-designer, brand-guardian, visual-storyteller |
| Sales | 8 | deal-strategist, discovery-coach, pipeline-analyst |
| Testing | 8 | reality-checker, accessibility-auditor, performance-benchmarker |
| Paid Media | 7 | ppc-strategist, programmatic-buyer, paid-social-strategist |
| Game Development | 16 | game-designer, unity-architect, godot-gameplay-scripter, unreal-systems-engineer |
| Project Management | 6 | project-manager-senior, studio-producer, experiment-tracker |
| Support | 6 | support-responder, finance-tracker, infrastructure-maintainer |
| Spatial Computing | 6 | visionos-spatial-engineer, xr-immersive-developer |
| Product | 4 | sprint-prioritizer, feedback-synthesizer, trend-researcher |
| Strategy | 1 | nexus-strategy |
| Business | 5 | analytics-agent, content-agent, marketing-agent, operations-agent, sales-agent |

## Regenerate

Skills are generated from the agent `.md` files using the conversion script:

```bash
./scripts/convert.sh --tool skillssh
```

## Compatible With

Works with 45+ AI coding tools including Claude Code, Cursor, GitHub Copilot, Windsurf, and more.
