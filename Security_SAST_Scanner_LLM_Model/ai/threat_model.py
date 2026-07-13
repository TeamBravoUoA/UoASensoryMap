"""AI enrichment (plain-language explanations) """

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Models tried in priority order. Qwen-Coder first (supervisor's recommendation,
# used whenever available); GPT-OSS-20B is the reliable fallback; Llama is a last
# resort. All end in :free to stay on the free tier.
FALLBACK_MODELS = [
    "qwen/qwen3-coder:free",
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

MAX_RETRIES_PER_MODEL = 2   # quick retries on a busy (429) model before falling back
BASE_WAIT = 2               # base seconds for backoff


def _build_prompt(finding):
    """Turn a scanner finding into a prompt for the model.

    `finding` is a dict from the rule-based scanner, e.g.:
        {
            "rule": "raw-sql-query",
            "file": "views.py",
            "line": 42,
            "code": "query = \"... \" + user_input",
            "message": "Possible SQL injection",
        }
    """
    return (
        "You are a security code reviewer. A static analysis tool flagged the "
        "following issue. In 2-3 short sentences, explain the risk in plain "
        "language and suggest how to fix it.\n\n"
        f"Rule: {finding.get('rule', 'n/a')}\n"
        f"File: {finding.get('file', 'n/a')} (line {finding.get('line', 'n/a')})\n"
        f"Message: {finding.get('message', 'n/a')}\n"
        f"Code:\n{finding.get('code', 'n/a')}"
    )


def _call_model(model, prompt, api_key):
    """Make one request to a single model. Returns the requests.Response."""
    return requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )


def _try_model(model, prompt, api_key):
    """Try one model, with brief retries on rate-limit.

    Returns the answer text on success, or None to signal 'fall back'.
    """
    for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
        response = _call_model(model, prompt, api_key)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()

        # Busy: wait and retry the same model
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait = int(retry_after) if retry_after else BASE_WAIT * attempt
            time.sleep(wait)
            continue

        # Unavailable / paid-only / other error: don't retry, fall back
        return None

    return None  # exhausted retries on 429


def explain_finding(finding):
    """Enrich a single scanner finding with an AI explanation.

    Always returns a dict. On success it adds 'ai_explanation' and the model used.
    On failure it returns the finding unchanged with a note, so the caller can
    carry on regardless (the AI layer is optional).
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {**finding, "ai_explanation": None,
                "ai_note": "No API key set; skipped AI enrichment."}

    prompt = _build_prompt(finding)

    for model in FALLBACK_MODELS:
        answer = _try_model(model, prompt, api_key)
        if answer:
            return {**finding, "ai_explanation": answer, "ai_model": model}

    # Every model failed - return the finding unchanged, with a note
    return {**finding, "ai_explanation": None,
            "ai_note": "All AI models unavailable; rule-based finding only."}


# Manual check: run this file directly to confirm the connection works.
if __name__ == "__main__":
    sample = {
        "rule": "raw-sql-query",
        "file": "views.py",
        "line": 42,
        "code": "query = \"SELECT * FROM users WHERE name = '\" + user + \"'\"",
        "message": "Possible SQL injection from string concatenation",
    }
    result = explain_finding(sample)
    if result["ai_explanation"]:
        print(f"Model used: {result['ai_model']}\n")
        print(result["ai_explanation"])
    else:
        print(result["ai_note"])