# Security & Compliance Audit Swarm

> Claude Sonnet 4.6 · The Agency Multi-Agent Framework
> Production-Ready Security & Compliance Pipeline

**Build Date:** March 16, 2026
**Status:** ✅ Complete · 16/16 Tests Passing

---

## Overview

Multi-agent pipeline delivering comprehensive security audits through 5 specialized agents:

```
PM → Security Engineer → Compliance Auditor → QA → Claude Reasoning Core
```

| Capability | Details |
|---|---|
| **Threat Modeling** | STRIDE analysis, attack surface mapping, vulnerability assessment |
| **Compliance** | SOC 2, ISO 27001, GDPR, HIPAA, PCI-DSS readiness |
| **Structured Outputs** | 5 timestamped reports in `scaffold/security-audits/` |
| **CLI** | `--mission` + `--scope` arguments |
| **Integration** | The Agency patterns, deepagents SDK, Titans Memory |

---

## Quick Start

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
bash setup.sh

# Application-layer audit
python3 security_audit_swarm.py --mission "Audit REST API security" --scope application

# Full-spectrum audit
python3 security_audit_swarm.py --mission "SOC 2 readiness check" --scope full

# Dry run (no API calls)
python3 security_audit_swarm.py --mission "Test" --dry-run
```

---

## Pipeline

| Stage | Agent | Output | Focus |
|---|---|---|---|
| 1 | **PM** | `audit_plan.md` | Phases, timelines, risk-ranked priorities |
| 2 | **Security Engineer** | `threat_model.md` | STRIDE, OWASP Top 10, attack surfaces |
| 3 | **Compliance Auditor** | `compliance_report.md` | SOC 2, ISO 27001, GDPR, PCI-DSS |
| 4 | **QA** | `test_results.md` | Validation matrix, consistency checks |
| 5 | **Claude Reasoning Core** | `final_verdict.md` | GO / CONDITIONAL GO / NO-GO verdict |

Each agent receives all prior outputs, building on previous analysis.

---

## Audit Scopes

| Scope | Coverage |
|---|---|
| `application` | APIs, auth, data handling, injection, XSS |
| `infrastructure` | Network, cloud config, secrets, IAM, containers |
| `full` | Application + infrastructure + compliance + supply chain |

---

## Output Structure

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

Each report includes mission context, scope, timestamp, and model version.

---

## Compliance Frameworks

| Framework | Coverage |
|---|---|
| **OWASP Top 10** | Full — injection, auth, XSS, SSRF, etc. |
| **SOC 2** | Trust Service Criteria (Security, Availability, Confidentiality) |
| **ISO 27001** | Annex A controls — Information Security Management System |
| **GDPR** | Article 32 technical and organizational measures |
| **HIPAA** | Security Rule safeguards (where applicable) |
| **PCI-DSS** | Payment card data requirements (where applicable) |

---

## Tests

```bash
python3 tests/test_security_audit_swarm.py
```

16 tests covering:
- Script executability and syntax
- Agent pipeline definition and ordering
- CLI argument parsing
- Output directory creation
- Compliance framework references (OWASP, STRIDE, SOC 2, ISO 27001)
- Dry-run mode
- Verdict parsing

---

## Files

| File | Type | Status |
|---|---|---|
| `security_audit_swarm.py` | Main Script | ✅ Created |
| `SECURITY_AUDIT_SWARM.md` | Full Docs | ✅ Created |
| `tests/test_security_audit_swarm.py` | Test Suite | ✅ Created |
| `scaffold/security-audits/` | Output Dir | ✅ Created |

---

## Next Steps

1. **Test run:** `python3 security_audit_swarm.py --mission "Test audit" --dry-run`
2. **Live audit:** `python3 security_audit_swarm.py --mission "Audit Empress Properties API" --scope application`
3. **CI/CD integration:** Add pre-deploy security gates
4. **Quarterly cadence:** Schedule compliance audits

---

*Part of The Agency — Claude-Powered Multi-Agent Swarm Framework*
