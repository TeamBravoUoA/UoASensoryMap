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

The scanner has three pillars, feeding a shared AI enrichment layer (see architecture diagram):

### Pillar 1 — SAST: Rule-based scanner (Python, AST parsing)

19 detection rules, grounded in established cybersecurity standards:

- OWASP Top 10 (most critical security risks to web applications)
- OWASP Code Review Guide
- OWASP Testing Guide
- Web Application Security Considerations
- CWE (Common Weakness Enumeration) references where applicable

**How it works:**

1. Every `.py` file in the project is parsed into an AST (Abstract Syntax Tree) — Python's own internal representation of the code's structure
2. Each rule walks the tree looking for a specific dangerous pattern — a hardcoded secret, a call to `eval()`, a missing permission check, etc.
3. Matched patterns are reported as a Finding (rule ID, severity, attack technique, file/line, message, standard reference)
4. Findings are passed through an AI enrichment layer for a plain-language explanation and suggested fix, then formatted into a Markdown report and posted automatically as a PR comment

**Scope:** static analysis only — the scanner reads code structure, it never executes any of the code it scans. 

### Pillar 2 — IaC: Infrastructure as Code (Checkov)

Open-source IaC scanner (Checkov), configured to scan Terraform (`.tf`) files.

Since UoA Sense Map does not currently provision infrastructure via Terraform, a demonstration file (`infra/demo.tf`) provides 3 paired True Positive / True Negative configuration samples — network exposure, encryption at rest, and IAM least-privilege — to verify the scanning integration end-to-end.

**How it works:**

1. Checkov reads `.tf` files in the `infra/` folder and checks each resource block against its built-in rule library (network exposure, encryption, IAM permissions, and more)
2. Findings are captured from Checkov's own output and formatted consistently with the SAST and SCA pillars' reports
3. Runs as part of the same CI/CD pipeline, alongside SAST and SCA

**Scope:** UoA Sense Map does not currently provision infrastructure via Terraform (deployment is Gunicorn + WhiteNoise, no cloud IaC in place). A demonstration file (`infra/demo.tf`) provides 3 paired True Positive / True Negative configuration samples — network exposure, encryption at rest, and IAM least-privilege — to verify the scanning integration end-to-end. This file is not real infrastructure and should never be applied; it exists only to prove the tooling works correctly, so the pillar is ready to adopt if the project's deployment.

---

### Pillar 3 — SCA: Third-Party Dependency Scanning (OSV API)

Checks every package pinned in `requirements.txt` against the [OSV (Open Source Vulnerabilities) database](https://osv.dev) — a free, public vulnerability database maintained by Google, covering PyPI (the official registry Python packages are published to and installed from) and other language ecosystems.

Grounded in:

- OWASP Top 10:2025 A03 – Software Supply Chain Failures
- OWASP Code Review Guide

**How it works:**

1. Parse `requirements.txt` to extract each package name and pinned version
2. Query the OSV API for each package/version pair
3. Any matched CVE is reported as a Finding (package, version, CVE ID, severity), reusing the same reporting format as the SAST and IaC pillars
4. Runs as part of the same CI/CD pipeline, alongside SAST and IaC

**Scope:** scans every package listed in `requirements.txt` — this includes packages you directly chose (Django, DRF, Pillow, psycopg2-binary) as well as packages pulled in as dependencies of those but still explicitly pinned in the file (e.g. asgiref, sqlparse). Any package NOT listed in requirements.txt — i.e. resolved silently at install time without being pinned — falls outside this scanner's current scope, along with broader supply-chain integrity checks (unpinned versions, unhashed packages, CI Action pinning).Detecting these would require dynamic analysis (actually installing dependencies and inspecting the resolved environment), which is out of scope for this static analysis scanner.

### Layer 2: AI enrichment

This part of the scanner takes a security finding (produced by the rule-based
scanner) and asks a hosted language model, via the OpenRouter API, to explain it
in plain language and suggest a fix.

Design notes:
- The AI layer is **additive**. If it fails (model busy, deprecated, or offline),
  the caller still has the original rule-based finding — detection never depends
  on it. Its role is to translate findings (vulnerabilities and recommendations)
  into plain language that everyone can understand, not only developers.
- Models are tried in priority order (fallback list). A "busy" model (429) is
  retried briefly; an "unavailable" model (402/404) is skipped immediately.
- The API key is read from the environment (`.env`), never hardcoded.

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
├── infra/
│   └── demo.tf                  # True Positives (TP)/True Negatives(TN) for IaC functionality validation.         
│                                # Checkov's
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
python -m demo.py

## Tools

SAST
- **Python / Django** — the application under analysis and the language the scanner is written in.

IaC
- **checkov** — performed with Checkov, an open-source IaC scanner. 
              —  Vendor (Palo Alto Networks)
              —  Framework scanned: Terraform (HashiCorp)

SCA
- **OSV API** — vulnerability database queried by the SCA layer for known CVEs.

LLM from Open AI
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
