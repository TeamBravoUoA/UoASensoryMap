import sys
sys.path.append("Security_Scanner_SAST_IaC_SCA_LLM")

import ast
from scanner.sast_scanner import check_security_misconfig


def run_check(label, code_or_path, is_file=False):
    print(f"\n--- {label} ---")
    if is_file:
        with open(code_or_path) as f:
            source = f.read()
    else:
        source = code_or_path

    tree = ast.parse(source)
    findings = check_security_misconfig(tree, code_or_path if is_file else "demo_snippet.py")

    if findings:
        print(f"{len(findings)} issue(s) found:")
        for f in findings:
            print(f"  [{f.severity}] {f.rule_id} (line {f.line}): {f.message}")
    else:
        print("No issues found.")


# 1. Real project settings — should mostly pass
run_check("Real settings.py", "UoASensoryMap/settings.py", is_file=True)

# 2. Fabricated TP examples — should each be flagged
run_check("Fabricated: DEBUG = True", "DEBUG = True")
run_check("Fabricated: hardcoded SECRET_KEY", 'SECRET_KEY = "django-insecure-abc123"')
run_check("Fabricated: empty ALLOWED_HOSTS", "ALLOWED_HOSTS = []")
run_check("Fabricated: wildcard ALLOWED_HOSTS", "ALLOWED_HOSTS = ['*']")