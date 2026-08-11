## 🔎 Security Scanner Results

Scanned **18** files.
**3 issue(s) found:**

### [Critical] `SEC-MISCONFIG-SECRET-KEY-FALLBACK`
**File:** `..\UoASensoryMap\settings.py:32`
**Standard:** OWASP Top 10:2025 A02 – Security Misconfiguration

> SECRET_KEY is loaded from an environment variable, but a hardcoded fallback value is provided. If the environment variable is ever unset, the app will sillently run with this fallback value, which is visible in source control.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
If the `SECRET_KEY` environment variable is ever missing, the application silently falls back to a hard‑coded key that lives in the repository. That key is predictable and publicly visible, letting anyone who can read the code forge session cookies, tamper with signed data, or bypass authentication.

**Concrete fix**  
Remove the fallback value and force the application to fail loudly when the key is not supplied. Optionally generate a random key at first run and store it securely.

```python
# ..\UoASensoryMap\settings.py

import os
from django.core.exceptions import ImproperlyConfigured

def get_env_variable(var_name: str) -> str:
    """Get the environment variable or raise an error."""
    try:
        return os.environ[var_name]
    except KeyError:
        raise ImproperlyConfigured(
            f"Set the {var_name} environment variable"
        )

# Use the helper to load SECRET_KEY
SECRET_KEY = get_env_variable("DJANGO_SECRET_KEY")

# Optional: generate a random key on first run and store it securely
# (e.g., in a secrets manager or a protected file)
```

With this change, the application will stop if the key is missing, preventing accidental deployment with a weak, hard‑coded secret.

---

### [Critical] `SEC-MISCONFIG-ALLOWED-HOSTS-FALLBACK`
**File:** `..\UoASensoryMap\settings.py:37`
**Standard:** OWASP Top 10:2025 A02 – Security Misconfiguration

> _ALLOWED_HOSTS is loaded from an environment variable, but a hardcoded fallback value is provided. If the environment variable is ever unset, the app will sillently run with this fallback value, which is visible in source control.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
`ALLOWED_HOSTS` tells Django which hostnames the application will accept. If the environment variable that should supply this list is missing, the hard‑coded fallback is used automatically. That means the app will run with a predictable, potentially insecure host list that is visible in the repository, exposing the site to host‑header attacks and making the configuration hard to change without editing code.

**Concrete fix**  
Remove the fallback and force the application to fail (or use an empty list) when the environment variable is not set. This ensures the deployment environment must explicitly provide a safe value.

```python
# settings.py
import os
from django.core.exceptions import ImproperlyConfigured

# ------------------------------------------------------------------
# ALLOWED_HOSTS
# ------------------------------------------------------------------
# The environment variable must be set; otherwise raise an error.
env_allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS")
if not env_allowed_hosts:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS environment variable is required but not set."
    )

# Convert the comma‑separated string into a list of hostnames.
ALLOWED_HOSTS = [host.strip() for host in env_allowed_hosts.split(",") if host.strip()]

# ------------------------------------------------------------------
# (Optional) If you want to allow all hosts in a development environment,
# you can add a separate flag, e.g. DJANGO_ALLOW_ALL_HOSTS=true.
# ------------------------------------------------------------------
```

*Explanation of the change:*  
- The code now requires the `DJANGO_ALLOWED_HOSTS` variable; if it is missing, the application will not start, preventing accidental exposure.  
- The list is built from the environment value, so the hard‑coded fallback is eliminated and the configuration is no longer visible in source control.

---

### [Medium] `SEC-MISCONFIG-ALLOWED-HOSTS-DYNAMIC`
**File:** `..\UoASensoryMap\settings.py:38`
**Standard:** OWASP Top 10:2025 A02 – Security Misconfiguration

> ALLOWED_HOSTS is built dynamically (e.g. via a list comprehension over an environment variable) rather than as a plain list literal. This rule cannot verify what value it actually resolves to without running the code, so a dangerous default hidden inside the expression — e.g. os.getenv('ALLOWED_HOSTS', '*') falling back to a wildcard if the environment variable is unset — would go completely undetected. Manually confirm the fallback value used here is a safe, explicit domain list, not an empty string or '*'.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
`ALLOWED_HOSTS` tells Django which hostnames are allowed to serve the site. If it ends up as `['*']` (or an empty string that resolves to `['*']`), the application will accept requests from any host, exposing it to Host‑Header attacks, click‑jacking, and other security risks. A dynamic expression that can silently fall back to a wildcard is hard to audit and can hide a dangerous default.

**Concrete fix**  
Replace the dynamic construction with a clear, explicit list (or a safe parsing routine that never defaults to `'*'`). For example:

```python
# settings.py

import os

# Explicitly list the allowed hosts.  Add your production domains here.
ALLOWED_HOSTS = [
    "example.com",
    "www.example.com",
    # Add any other trusted domains
]

# If you still want to allow an env‑var override, do it safely:
env_hosts = os.getenv("ALLOWED_HOSTS")
if env_hosts:
    # Split on commas, strip whitespace, and reject any wildcard entry
    parsed = [h.strip() for h in env_hosts.split(",") if h.strip() and h.strip() != "*"]
    if parsed:
        ALLOWED_HOSTS = parsed
```

This guarantees that `ALLOWED_HOSTS` can never contain a wildcard unless you explicitly add it, making the configuration safe and auditable.

---
