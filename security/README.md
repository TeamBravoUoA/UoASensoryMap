# Embedded Security Scanner

A custom security scanner for the UoA Sensory Map application, run as part of CI to
analyse the project's own codebase for security issues.

## How to run
python -m security

## Tools

- **Python / Django** — the application under analysis and the language the scanner is written in.
- **Ollama (running locally) with Mistral 7B** — used for the AI reasoning step (Phase 2).
  Chosen because it runs fully offline, free, and on local hardware: no API costs, and the
  codebase never leaves the machine. 

## Design decisions

A hosted LLM API (Claude Opus) was considered but rejected on cost and data-privacy grounds for a
student project. The AI reasoning step therefore runs locally via Ollama (see Tools).

## Roadmap

- **MVP (Week 3, internal; demo to guides Week 4):** static analysis (SAST) of the
  codebase plus a dependency audit, with findings posted to pull requests via CI.
- **v1.1 (Week 5 onwards):** AI-assisted reasoning using a local Ollama model. 
  Important!pending a spike to confirm it can run in CI.

## Standards referenced

The detection rules and review techniques are informed by:

- OWASP Top 10 — most critical security risks to web applications
- OWASP Testing Guide
- OWASP Code Review Guide
- Web Application Security Considerations (provided by the University in the project brief)
