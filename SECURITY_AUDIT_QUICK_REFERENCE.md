# Security Audit Swarm — Quick Reference

## One-Liner Commands

```bash
# Full-spectrum audit (application + infrastructure + compliance + supply chain)
python3 security_audit_swarm.py --mission "Full SOC 2 readiness check" --scope full

# Application-layer audit (APIs, auth, data handling, injection, XSS)
python3 security_audit_swarm.py --mission "Audit REST API security" --scope application

# Infrastructure audit (network, cloud config, secrets, IAM, containers)
python3 security_audit_swarm.py --mission "Audit cloud infrastructure" --scope infrastructure

# Compliance-only audit
python3 security_audit_swarm.py --mission "GDPR compliance review" --scope compliance

# Dry run (no API calls — validates pipeline without LLM)
python3 security_audit_swarm.py --mission "Test" --dry-run
```

## Agent Pipeline

```
Stage 1: PM                    → audit_plan.md         (phases, timelines, risk priorities)
Stage 2: Security Engineer     → threat_model.md       (STRIDE, OWASP Top 10, attack surfaces)
Stage 3: Compliance Auditor    → compliance_report.md  (SOC 2, ISO 27001, GDPR, PCI-DSS)
Stage 4: QA                    → test_results.md       (validation matrix, consistency checks)
Stage 5: Claude Reasoning Core → final_verdict.md      (GO / CONDITIONAL GO / NO-GO)
```

Each agent receives all prior outputs, building on previous analysis.

## Output Files

Reports are written to `scaffold/security-audits/<timestamp>/`:

```
scaffold/security-audits/
└── 20260316_143000/
    ├── audit_plan.md
    ├── threat_model.md
    ├── compliance_report.md
    ├── test_results.md
    ├── final_verdict.md
    └── manifest.json
```

## CI/CD Integration

The `security-gate.yml` workflow runs on every push to `main` and on pull requests:

```yaml
# .github/workflows/security-gate.yml
- Validates security_audit_swarm.py syntax
- Runs tests/test_security_audit_swarm.py (16 tests)
- Executes dry-run to verify pipeline integrity
```

Blocks merge if any step fails.

## Troubleshooting

| Issue | Fix |
|---|---|
| `ANTHROPIC_API_KEY not set` | `export ANTHROPIC_API_KEY="sk-ant-..."` |
| `Agent file missing` | Run `bash setup.sh` to ensure all agent `.md` files are present |
| `Output directory error` | `mkdir -p scaffold/security-audits/` — the script creates this automatically |
| `ModuleNotFoundError` | `pip install -e deepagents/libs/deepagents && pip install langchain-anthropic` |
| `Dry-run passes but live fails` | Check API key validity and rate limits |

## Glossary

| Term | Definition |
|---|---|
| **STRIDE** | Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege — Microsoft threat modeling framework |
| **OWASP Top 10** | Open Web Application Security Project's top 10 web application security risks |
| **SOC 2** | Service Organization Control 2 — trust service criteria for security, availability, confidentiality |
| **ISO 27001** | International standard for Information Security Management Systems (ISMS) |
| **GDPR** | General Data Protection Regulation — EU data privacy and protection law |
| **HIPAA** | Health Insurance Portability and Accountability Act — US healthcare data protection |
| **PCI-DSS** | Payment Card Industry Data Security Standard — requirements for handling card data |

---

*Part of The Agency — Claude-Powered Multi-Agent Swarm Framework*
