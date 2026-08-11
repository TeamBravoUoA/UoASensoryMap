# Embedded Security Scanner

A custom security scanner for the UoA Sensory Map application, run as part of CI to
analyse the project's own codebase for security issues.

## Scanning Technique to use
- The scanner implements three methodologies: SAST (static analysis of the application's own source code, via AST parsing), SCA (software composition analysis of third-party dependencies against known Common Vulnerabilities and Exposures / CVE), and IaC (infrastructure-as-code and CI/CD configuration checks, delegated to an external tool rather than custom AST parsing).
- Dynamic methods (DAST, IAST) are out of scope, as they require a running,instrumented application.

## Outputs

The scanner reports the vulnerabilities found and recommendations in plain language,
so anyone can understand them — not only developers.

## Scanner design

### Layer 1: Rule-based scanner (Python)

Detection rules based on cybersecurity standards from OWASP:

- Web Application Security Considerations
- OWASP Code Review Guide
- OWASP Top 10 (most critical security risks to web applications)
- OWASP Testing Guide

### Layer 2: AI enrichment

This part of the scanner takes a security finding (produced by the rule-based
scanner) and asks a hosted language model, via the OpenRouter API, to explain it
in plain language and suggest a fix.

Design notes:
- The AI layer is **additive**. If it fails (model busy, withdrawn, offline), the
  caller still has the original rule-based finding. We never depend on it for
  detection. Its role is to translate the findings (vulnerabilities and
  recommendations) into plain language that everyone can understand, not only
  developers.
- Models are tried in priority order (fallback list). A "busy" model (429) is
  retried briefly; an "unavailable" model (402/404) is skipped immediately.
- The API key is read from the environment (.env), never hard-coded.

## Architecture

security/
├── __main__.py                 # Entry point — runs the scanner (python -m security)
├── scanner/
│   ├── __init__.py
│   └── sast_scanner.py         # Pillar 1 — SAST: static analysis of the code (AST parsing)
├── dependencies/
│   ├── __init__.py
│   └── sca_scanner_dependencies.py   # Pillar 2 — SCA: dependency / Common Vulnerabilities & Exposures (known-CVE audit (OSV))
├── iac/
│   ├── __init__.py
│   └── iac_scanner.py          # Pillar 3 — IaC: infrastructure-as-code / CI-CD config
│                                #             checks (delegated to checkov as a CI step,
│                                #             output normalised into the shared Finding shape)
├── ai/
│   ├── __init__.py
│   ├── test_qwen.py
│   └── threat_model.py         # Layer 2 — AI enrichment (plain-language explanations)
└── tests_security_sast_sca_iac/
    ├── __init__.py
    ├── test_sast.py
    ├── test_sca.py
    ├── test_iac.py
    └── fixtures/
        └── iac/
            ├── insecure_sg.tf  # True Positivie fixture — proves the Terraform-check capability
            └── secure_sg.tf    # True Negative fixture — since the app itself has no real .tf files

**Note on IaC scope:** IaC scanning was added beyond the project's original requirements to push the scanner's scope and difficulty further, as a third
pillar alongside SAST and SCA. The deployment is PaaS-based, so the pillar targets real config where it applies — GitHub Actions workflows
(`.github/workflows/*.yml`) — and validates its Terraform-checking logic against synthetic `.tf` fixtures (`tests_security_sast_sca_iac/fixtures/iac/`),
using the same True Positive / True Negative approach applied to every other rule in the scanner.

## How to run
python -m security

## Tools

- **Python / Django** — the application under analysis and the language the scanner is written in.
- **OSV API** — vulnerability database queried by the SCA layer for known CVEs.
- **checkov** — external IaC scanner wrapped by the IaC layer, delegated to rather than custom-built.
- **OpenRouter** — API gateway and key provider for Layer 2.
- **LLM providers** — GPT-OSS from OpenAI (main model, connecting successfully), Qwen (recommended model trying second) and Llama (trying third)

## Design decisions

- Local model hosting (Ollama) was the initial plan but was blocked by the
development machine's device security policy (Smart App Control / Device Guard),
which cannot be disabled without reinstalling Windows. 
- The AI pillar therefore uses a hosted API via OpenRouter. This trades some data privacy (code is sent to a third party) for capability and easier CI integration — a documented compromise for a student project. 
- A production security tool would likely favour local or self-hosted inference for data confidentiality.

## Standards referenced

The detection rules and review techniques are informed by:

- OWASP Top 10:2025 — most critical security risks to web applications
- OWASP Testing Guide
- OWASP Code Review Guide
- CWE (Common Weakness Enumeration) — for rules not covered by an OWASP Top 10 category (e.g. ReDoS, resource exhaustion)
- Web Application Security Considerations (provided by the University in the project brief)