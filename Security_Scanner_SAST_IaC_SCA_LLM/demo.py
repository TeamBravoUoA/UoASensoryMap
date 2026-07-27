import ast
from pathlib import Path
from scanner.sast_scanner import check_security_misconfig
from ai.threat_model import enrich_findings

PROJECT_ROOT = Path("..")  # one level up from Security_Scanner_SAST_IaC_SCA_LLM = the repo root
# Set this to True while developing/debugging, False for a clean demo run
VERBOSE = True

CHECKED_ATTACK_TYPES = [
    "SEC-MISCONFIG-DEBUG",
    "SEC-MISCONFIG-SECRET-KEY",
    "SEC-MISCONFIG-ALLOWED-HOSTS-EMPTY",
    "SEC-MISCONFIG-ALLOWED-HOSTS-WILDCARD",
]

all_findings = []
files_scanned = 0

for py_file in PROJECT_ROOT.rglob("*.py"):
    # Skip migrations, virtual environment, scanner files - not meaningful to scan 
    if (
        "migrations" in py_file.parts #Skip data migrations
        or ".venv" in py_file.parts #Skip Virtual environments
        or "__pycache" in py_file.parts # Skip folder python created everytime a .py file is run. Pre-complied version of the code (bytecode)
        or "Security_Scanner_SAST_IaC_SCA_LLM" in py_file.parts #Dont scan the scanner itself
    ) :

        continue 

    with open(py_file, encoding="utf-8") as f:
        source = f.read()


    try:
        tree = ast.parse(source)
    except SyntaxError:
        continue #skip any file that fails to parse

    files_scanned += 1
    findings = check_security_misconfig(tree, str(py_file))

    if VERBOSE:
        status = f"{len(findings)} issue (s)" if findings else "clean"
        checked_list = ", ".join(CHECKED_ATTACK_TYPES)
        print(f"[checked] {py_file} -> {status} (checked against: {checked_list})")

    all_findings.extend (findings)

print (f"Scanned {files_scanned} files across the UoA Sense Map codebase.\n")
print(f"{len(all_findings)} issue(s) found.\n")

if all_findings:
    print(f"{len(all_findings)} issue(s) found:")
    for f in all_findings:
        print (f"[{f.severity}] {f.rule_id} — {f.file_path}:{f.line}")
        print (f"{f.message}")
        print(f"      Standard: {f.standard_ref}")

else:
    print ("No security issues found across the entire scanned codebase")

#Report with LLM model in based on scanner findings output
if all_findings:
    print("\n--- AI-enriched explanations ---\n")
    enriched = enrich_findings(all_findings)
    for item in enriched:
        print(f"[{item['severity']}] {item['rule_id']} — {item['file_path']}:{item['line']}")
        if item["ai_explanation"]:
            print(f"(enriched by {item['ai_model']})")
            print(item["ai_explanation"])
        else:
            print(f"({item['ai_note']})")
            print(item["message"])
        print()