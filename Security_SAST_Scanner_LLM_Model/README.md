# Embedded Security Scanner

A custom security scanner for the UoA Sensory Map application, run as part of CI to
analyse the project's own codebase for security issues.

## Scanning Technique to use
- The scanner implements two static application security testing methodologies: SAST (static analysis of the application's own source code, via AST parsing) and SCA (software composition analysis of third-party dependencies against known vulnerabilities).
- Dynamic methods (DAST, IAST) are out of scope, as they require a running, instrumented application

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

## Arquitecture 
## Architecture

security/
├── __main__.py          # Entry point — runs the scanner (python -m security)
├── scanner/
│   └── sast_scanner.py   # Layer 1 — SAST: static analysis of the code (AST)
├── dependencies/
│   └── sca_audit.py      # Layer 1 — SCA: dependency / known-CVE audit
├── ai/
│   └── threat_model.py   # Layer 2 — AI enrichment (plain-language explanations)
└── tests_scanner/        # Tests for the scanner itself

**Flow:** `__main__.py` runs the two Layer 1 components (SAST + SCA) to
produce findings, passes them to Layer 2 (`threat_model.py`) for AI
explanations, and outputs a combined report to the pull request.

## How to run
python -m security

## Tools

- **Python / Django** — the application under analysis and the language the scanner is written in.
- **OpenRouter** — API gateway and key provider.
- **LLM providers** — Qwen (supervisor's recommended model, tried first), GPT-OSS from OpenAI (main model, connecting successfully), and Llama as fallback.

## Design decisions

- Local model hosting (Ollama) was the initial plan but was blocked by the
development machine's device security policy (Smart App Control / Device Guard),
which cannot be disabled without reinstalling Windows. 
- The AI pillar therefore uses a hosted API via OpenRouter. This trades some data privacy (code is sent to
a third party) for capability and easier CI integration — a documented compromise
for a student project. 
- A production security tool would likely favour local or
self-hosted inference for data confidentiality.

## Roadmap

- **Pre-setup — LLM model research:** evaluated local hosting (Ollama) vs hosted
  API, CI feasibility, and model connection type. Local hosting was blocked by
  device security policy, so the AI pillar uses a hosted API (OpenRouter).
- **MVP (Week 3 internal; demo to supervisors Week 4):** static analysis (SAST)
  of the codebase plus a dependency audit, with findings posted to pull requests
  via CI.
- **v1.1 (Week 5 onwards):** AI-assisted reasoning that enriches scanner findings
  with plain-language explanations, via a hosted LLM (OpenRouter, with model
  fallback). Pending a spike to confirm the API call works reliably in CI.

## Standards referenced

The detection rules and review techniques are informed by:

- OWASP Top 10 — most critical security risks to web applications
- OWASP Testing Guide
- OWASP Code Review Guide
- Web Application Security Considerations (provided by the University in the project brief)