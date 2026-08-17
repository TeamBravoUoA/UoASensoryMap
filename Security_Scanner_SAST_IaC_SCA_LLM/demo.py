# Note: despite the name, this file also acts as run_scan.py for
# GitHub Actions — it's the actual entry point the CI workflow runs.

import ast
from pathlib import Path
from scanner.sast_scanner import check_security_misconfig
from scanner.sast_scanner import check_hardcoded_secrets
from scanner.sast_scanner import check_unsafe_eval_exec
from scanner.sast_scanner import check_insecure_deserialization
from scanner.sast_scanner import check_weak_hashing
from scanner.sast_scanner import check_unsafe_image_upload
from scanner.sast_scanner import check_redos_unsafe_regex
from scanner.sast_scanner import check_missing_timeout
from scanner.sast_scanner import check_silent_fail_open
from scanner.sast_scanner import check_sql_injection
from scanner.sast_scanner import check_ssrf
from scanner.sast_scanner import check_csrf_exempt, check_permissive_cors
from scanner.sast_scanner import check_cookie_security_flags
from scanner.sast_scanner import check_unbounded_slice
from scanner.sast_scanner import check_missing_auth_decorators
from scanner.sast_scanner import check_idor_missing_permission
from ai.threat_model import enrich_findings
from format_report import format_report_markdown


PROJECT_ROOT = Path("..")  # one level up from Security_Scanner_SAST_IaC_SCA_LLM = the repo root
# Set this to True while developing/debugging, False for a clean demo run
VERBOSE = True

CHECKED_ATTACK_TYPES = [
    "SEC-MISCONFIG-DEBUG",
    "SEC-MISCONFIG-SECRET-KEY",
    "SEC-MISCONFIG-ALLOWED-HOSTS-EMPTY",
    "SEC-MISCONFIG-ALLOWED-HOSTS-WILDCARD",
    "SEC-MISCONFIG-ALLOWED-HOSTS-DYNAMIC",
    "SEC-MISCONFIG-SSL-HSTS-MISSING",
    "SEC-MISCONFIG-SECRET-KEY-FALLBACK",
    "SEC-MISCONFIG-ALLOWED-HOSTS-FALLBACK",
    "SEC-MISCONFIG-HARDCODED-SECRET",
    "SEC-UNSAFE-EVAL-EXEC",
    "SEC-INSECURE-DESERIALIZATION-PICKLE",
    "SEC-WEAK-HASHING-ALGORITHM",
    "SEC-UNSAFE-IMAGE-UPLOAD", 
    "SEC-UNSAFE-REGEX-EXPRESSIONS", 
    "SEC-RESOURCE-STARVATION", 
    "SEC-SEC-SILENT-FAIL-OPEN", 
    "SEC-SQL-INJECTION", 
    "SEC-SSRF-USER-CONTROLLED-URL", 
    "SEC-CSRF-EXEMPT-DJANGO-SECURITY",
    "SEC-CSRF-PERMISSIVE-CORS/API-ACCESS-ANYWEBSITE",
    "SEC-MISSING-COOKIE-FLAGS", 
    "SEC-UNBOUNDED-SLICE/DoS-MEMORY-EXAHUSTATION",
    "SEC-MISSING-AUTH-DECORATOR/BROKEN-ACCESS-CONTROL-PERMISSION-CLASSES",
    "SEC-IDOR-MISSING-PERMISSION-CHECK/BROKEN-ACCESS-CONTROL-IDOR-OBJECT-ACCESS"
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

    #Rules checking the same AST node type CAN be bundled into one function
    #to avoid walking the tree twice — but this is a choice, not a strict
    #rule (check_unsafe_eval_exec and check_insecure_deserialization both
    #walk Call nodes too, but were kept separate since they're unrelated).
    files_scanned += 1
    #Containing Rules:env-fallback watchlist, DEBUG, SECRET_KEY, ALLOWED_HOSTS (×3 variants: empty/wildcard/dynamic), and SSL/HSTS
    findings = check_security_misconfig(tree, str(py_file))
    #Containing rules: SEC-MISCONFIG-HARDCODED-SECRET
    findings += check_hardcoded_secrets(tree, str(py_file))
    #Containing rules:DANGEROUS CALLS - eval() / exec ()
    findings += check_unsafe_eval_exec(tree, str(py_file))
    #Containing rules : DANGEROUS_DESERIALIZE_CALLS pickle.loads
    findings += check_insecure_deserialization(tree, str(py_file))
    #Containing rule: SEC-WEAK-HASING-ALROFITHM (hashlib.md5 / hashlib.sha1)
    findings += check_weak_hashing(tree, str(py_file))
    #Containing rule: SEC-UNSAFE-IMAGE-UPLOAD (Image.open() on request.FILES with no validation)
    findings += check_unsafe_image_upload(tree, str(py_file))
    #Containing rule: SEC-REDOS-UNSAFE-REGEX (nested quantifier regex patterns)
    findings += check_redos_unsafe_regex(tree, str(py_file))
    #Containing rule: SEC-MISSING-TIMEOUT (requests.* calls with no timeout=)
    findings += check_missing_timeout(tree, str(py_file))
    #Containing rule: SEC-SILENT-FAIL-OPEN (bare/empty except blocks)
    findings += check_silent_fail_open(tree, str(py_file))
    #Containing rule SEC-SQL-INJECTION (cursor.execute() with concatenated/f-string query)
    findings +=check_sql_injection(tree, str(py_file))
    #Containing rule: SEC-SSRF-USER-CONTROLLED-URL (requests.* with URL from request data)
    findings += check_ssrf(tree, str(py_file))
    #Containing rule: SEC-CSRF-EXEMPT (@csrf_exempt decorator)
    findings += check_csrf_exempt(tree, str(py_file))
    #Containing rule: SEC-PERMISSIVE-CORS (CORS_ALLOW_ALL_ORIGINS / wildcard)
    findings += check_permissive_cors(tree, str(py_file))
    #Containing rule: SEC-MISSING-COOKIE-FLAGS (HttpOnly/Secure/SameSite absence)
    findings += check_cookie_security_flags(tree, str(py_file))
    #Containing rule: SEC-UNBOUNDED-SLICE (unbounded queryset slice upper bound/data request boundaries)
    findings += check_unbounded_slice(tree, str(py_file))
    #Containing rule: SEC-MISSING-AUTH-DECORATOR (missing/AllowAny permission_classes on DRF views)
    findings += check_missing_auth_decorators(tree, str(py_file))
    #Containing rule: SEC-IDOR-MISSING-PERMISSION-CHECK (fetch-by-ID with no ownership check)
    findings += check_idor_missing_permission(tree, str(py_file))



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
#AI enrich findings reusable for both console output and markdown report

if all_findings:
    enriched = enrich_findings (all_findings)
else:
    enriched = []

if enriched:
    print ("\n ---AI-enriched explanations ---\n")
    for item in enriched:
        print (f"[{item['severity']}] {item['rule_id']} - {item['file_path']}:{item['line']}")
        if item["ai_explanation"]:
            print (f"(enriched by {item['ai_model']})")
            print (item["ai_explanation"])
        else:
            print (f"({item['ai_note']})")
            print (item["message"])
        print ()
    
report = format_report_markdown(enriched, files_scanned)
print("\n\n=== MARKDOWN PREVIEW ===\n")
print(report)

with open ("scan_report.md", "w", encoding = "utf-8") as f:
    f.write (report)

