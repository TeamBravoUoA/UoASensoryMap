## 🔎 Security Scanner Results

Scanned **21** files.
**5 issue(s) found:**

### [Critical] `SEC-MISCONFIG-SECRET-KEY-FALLBACK`
**File:** `..\UoASensoryMap\settings.py:32`
**Attack Type Exposure:** Session/Cookie Forgery
**Standard:** OWASP Top 10:2025 A02 – Security Misconfiguration

> SECRET_KEY is loaded from an environment variable, but a hardcoded fallback value is provided. If the environment variable is ever unset, the app will sillently run with this fallback value, which is visible in source control.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
If the `SECRET_KEY` environment variable is missing, the application will silently fall back to a hard‑coded key that is checked into source control. This key is the same for every deployment, making the app vulnerable to brute‑force or replay attacks and exposing the key to anyone who can read the repository.

**Concrete fix**  
Remove the fallback value and force the application to fail loudly when the key is not set.  
```python
# settings.py – line 32
import os
from django.core.exceptions import ImproperlyConfigured

def get_env_variable(var_name):
    """Get the environment variable or raise an error."""
    try:
        return os.environ[var_name]
    except KeyError:
        raise ImproperlyConfigured(f"Set the {var_name} environment variable.")

# Use the helper to load the secret key
SECRET_KEY = get_env_variable('DJANGO_SECRET_KEY')
```
Now the app will raise an error during startup if the key is missing, preventing accidental use of a weak, hard‑coded secret.

---

### [Critical] `SEC-MISCONFIG-ALLOWED-HOSTS-FALLBACK`
**File:** `..\UoASensoryMap\settings.py:37`
**Attack Type Exposure:** Host Header Injection
**Standard:** OWASP Top 10:2025 A02 – Security Misconfiguration

> _ALLOWED_HOSTS is loaded from an environment variable, but a hardcoded fallback value is provided. If the environment variable is ever unset, the app will sillently run with this fallback value, which is visible in source control.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
`ALLOWED_HOSTS` tells Django which hostnames the application will accept.  If the environment variable that should supply this list is missing, the hard‑coded fallback is used automatically.  That means the app will run with a potentially insecure set of hosts that is visible in source control, making it easier for attackers to target the site or for developers to accidentally expose the production URL.

**Concrete fix**  
Remove the fallback and force the application to fail loudly when the environment variable is not set.  Optionally, provide a clear error message that explains what needs to be configured.

```python
# ..\UoASensoryMap\settings.py

import os
from django.core.exceptions import ImproperlyConfigured

# ------------------------------------------------------------------
# ALLOWED_HOSTS
# ------------------------------------------------------------------
# The application must be explicitly configured with a list of hostnames.
# If the environment variable is missing, raise an error instead of
# silently falling back to a hard‑coded value.
env_var = "DJANGO_ALLOWED_HOSTS"
allowed_hosts_raw = os.getenv(env_var)

if allowed_hosts_raw is None:
    raise ImproperlyConfigured(
        f"Environment variable '{env_var}' is required but not set. "
        "Please provide a comma‑separated list of allowed hostnames."
    )

# Convert the comma‑separated string into a list, stripping whitespace.
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(",") if host.strip()]

# Example: if DJANGO_ALLOWED_HOSTS=example.com,api.example.com
# ALLOWED_HOSTS will be ['example.com', 'api.example.com']
```

This change ensures that the application will not start unless the required configuration is supplied, eliminating the insecure hard‑coded fallback.

---

### [Medium] `SEC-MISCONFIG-ALLOWED-HOSTS-DYNAMIC`
**File:** `..\UoASensoryMap\settings.py:38`
**Attack Type Exposure:** Host Header Injection
**Standard:** OWASP Top 10:2025 A02 – Security Misconfiguration

> ALLOWED_HOSTS is built dynamically (e.g. via a list comprehension over an environment variable) rather than as a plain list literal. This rule cannot verify what value it actually resolves to without running the code, so a dangerous default hidden inside the expression — e.g. os.getenv('ALLOWED_HOSTS', '*') falling back to a wildcard if the environment variable is unset — would go completely undetected. Manually confirm the fallback value used here is a safe, explicit domain list, not an empty string or '*'.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
`ALLOWED_HOSTS` tells Django which host headers are considered valid. If it ends up as `['*']` (the common wildcard fallback), the application will accept requests from any domain, exposing it to Host‑Header injection, click‑jacking, and other attacks that rely on trusting the host header. A dynamic expression that can silently resolve to a wildcard is therefore a hidden misconfiguration that static analysis can’t catch.

**Concrete code fix**  
Replace the dynamic construction with a clear, explicit list (or a safe environment‑based list that never falls back to `'*'`). For example:

```python
# settings.py

# 1. Prefer a hard‑coded list of allowed hosts
ALLOWED_HOSTS = [
    "example.com",
    "www.example.com",
    "api.example.com",
]

# 2. If you must read from an environment variable, enforce a safe default
#    and validate the value before using it.
import os

env_hosts = os.getenv("ALLOWED_HOSTS")
if env_hosts:
    # Split on commas and strip whitespace
    ALLOWED_HOSTS = [h.strip() for h in env_hosts.split(",") if h.strip()]
else:
    # Empty list means no hosts are allowed – safest default
    ALLOWED_HOSTS = []

# Optional: raise an error if the list is empty in production
if not ALLOWED_HOSTS and os.getenv("DJANGO_ENV") == "production":
    raise RuntimeError("ALLOWED_HOSTS cannot be empty in production")
```

This guarantees that the application never accepts arbitrary host headers and makes the configuration explicit and auditable.

---

### [Critical] `SEC-MISCONFIG-SSL-HSTS-MISSING`
**File:** `..\UoASensoryMap\settings.py:1`
**Attack Type Exposure:** SSL Stripping (Man-in-the-Middle)
**Standard:** OWASP Top 10:2025 A02 – Security Misconfiguration

> Missing HTTPS enforcement settings(s): SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS. Without these, traffic and session cookies (e.g. CMS admin login) can be intercepted via SSL stripping / man-in-the-middle attacks. Add SECURE_SSL_REDIRECT = True and SECURE_HSTS_SECONDS = 31536000.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
If your site does not force HTTPS and does not send the HSTS header, attackers can downgrade traffic to plain HTTP (SSL‑stripping) or intercept session cookies, letting them hijack admin sessions or steal sensitive data. Enabling these settings guarantees that browsers will only connect over HTTPS and will remember that rule for a long time.

**Concrete fix (settings.py)**  
```python
# ... existing settings ...

# Force all requests to use HTTPS
SECURE_SSL_REDIRECT = True

# Tell browsers to always use HTTPS for the next year (31536000 seconds)
SECURE_HSTS_SECONDS = 31536000
# Optional: include subdomains and allow pre‑loading
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```
Add these lines to your `settings.py` (or ensure they are set in your production environment) and restart the application. This will prevent SSL stripping and protect session cookies.

---

### [High] `SEC-MISSING-COOKIE-FLAGS`
**File:** `..\UoASensoryMap\settings.py:1`
**Attack Type Exposure:** Session Hijacking (Cookie Theft)
**Standard:** OWASP Top 10:2025 A04 – Cryptographic Failures

> Missing cookie security setting(s): SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE. Without these, session/CSRF cookies can be read by JavaScript (XSS-driven theft) or sent over plain HTTP (interception). Add SESSION_COOKIE_HTTPONLY = True, SESSION_COOKIE_SECURE = True, and CSRF_COOKIE_SECURE = True.

**AI Explanation** _(via openai/gpt-oss-20b:free)_:
**Why it matters**  
If session or CSRF cookies are not marked `HttpOnly` or `Secure`, a malicious script can read them (XSS theft) or an attacker can intercept them over an unencrypted HTTP connection. This can lead to session hijacking and cross‑site request forgery attacks.

**Concrete fix**  
Add the following lines to your `settings.py` (or ensure they exist) so that Django sets the proper flags on all cookies:

```python
# settings.py

# Prevent JavaScript from accessing session cookies
SESSION_COOKIE_HTTPONLY = True

# Require HTTPS for all session cookies
SESSION_COOKIE_SECURE = True

# Require HTTPS for CSRF protection cookie
CSRF_COOKIE_SECURE = True
```

Make sure your application is served over HTTPS; otherwise the `Secure` flag will prevent cookies from being sent.

---
