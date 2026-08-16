"""SAST (Static Application Security Testing (analysis of the application's own source code) 
via AST parsing (Abstract Syntax Tree) it reads the code the way python itself understands it - as structure, not text. Every piece of code becomes a "node" in a tree"""

# For every rule, there is one function assign to the main class (findings)
#Import findings file from main class 
from scanner.findings import Finding
#AST module for Abstract Syntax Tree functionality
import ast

#Variables where harcdoed fallback inside os.getenv ()/ os.environ.get() is considred unsafe, since each ends up feeding a security-sensitive setting. 
#Ad new variable names here if a similar risk is found elsewhere. 
ENV_FALLBACK_WATCHLIST = {
    "SECRET_KEY": {
        "rule_id": "SEC-MISCONFIG-SECRET-KEY-FALLBACK",
        "attack_type_exposure" : "Session/Cookie Forgery",
    },
    "_ALLOWED_HOSTS": {
        "rule_id": "SEC-MISCONFIG-ALLOWED-HOSTS-FALLBACK",
        "attack_type_exposure": "Host Header Injection",
    },
}

#Parameter tree as type ast.AST
#Parameter filepath as type str
def check_security_misconfig(tree: ast.AST, filepath: str) -> list [Finding]: #-> this function will return a list of finding objects
    findings = [] #Empty list which the function will fill up as it walks the three and returns at the end. 

    # ---RULE 4 SET UP:collects every variable name assigned anywhere in the file - needed
    #for rule 4, which can only be checked after seeing the whole file
    assigned_names = set()


    #ast.walk(tree) visit every single node in the whole three. Every function, imports, if-statements, etc.
    #The "node" variable becomes each of thise per iteration is a loop for every node in the code.
    for node in ast.walk(tree):
        #isistance = "Guard clause": isinstance(thing, SomeType) asks a yes/no question: "is thing of type SomeType?
        #It will return true or false
        #Skip anything that isnt an Assign node (x=y), so the rest of this loop can safely assume "node" is an assignment without extra nesting
        if not isinstance(node, ast.Assign):
            continue
        
        #node.targets is a list, not a single value
        for target in node.targets:
        #The target are only plain variable names node types (ast.Name like DEBUG)
            if not isinstance(target, ast.Name):
                continue

            # Record every assigned name for Rule 4 presente
            assigned_names.add(target.id)

            #--- Environment-variable hardcoded fallback check (Applicable to rule 1 & 2)---
            #Attack type covered: a variable is correctly loaded from an environment variable but hardcoded, unsafe literal is provided as the fallback value -
            #meaning  the "safe" pattern silently degrades if that env var is ever missing. Applies to any variable in ENV_FALLBACK_WATCHLIST
            if target.id in ENV_FALLBACK_WATCHLIST:
                if isinstance (node.value, ast.Call):
                    if isinstance (node.value.func, ast.Attribute) and node.value.func.attr in ("getenv", "get"):
                        if len (node.value.args) >= 2:
                            fallback_arg = node.value.args [1]
                            
                            #Only flag if the fallback is a real (non-empty) string literal. 
                            if isinstance (fallback_arg, ast.Constant) and isinstance (fallback_arg.value, str) and fallback_arg.value:
                                watchlist_entry = ENV_FALLBACK_WATCHLIST[target.id]
                                findings.append (Finding(
                                     rule_id= watchlist_entry["rule_id"],
                                     severity="Critical",
                                     attack_type_exposure=watchlist_entry["attack_type_exposure"],
                                     file_path=filepath,
                                     line=node.lineno,
                                     message=f"{target.id} is loaded from an environment variable, but a hardcoded fallback value is provided. If the environment variable is ever unset, the app will sillently run with this fallback value, which is visible in source control.", 
                                     standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",
                                     ))

                                 
            #---------TIER 1 START : Presence check (e.g. SECURE_SSL_REDIRECT, DEBUG, etc)----
            #judged from assignments alone — either one assignment's own value (flat literal), or whether a name was assigned anywhere at all (presence). 
            # No function calls, no argument inspection, no structural walking.

            # ---RULE 1 Attack type Security misconfiguration — DEBUG ----
            # Attack type covered: information disclosure via debug error pages —leaking stack traces and internal app structure to any visitor.

            # DEBUG is a setting in settings.py that controls how Django behaves when something goes wrong. It was two different modes. 
            # DEBUG = TRUE When an error happens, instead of a plain "Something went wrong" page, Django shows a detailed, interactive error page right in the browser
            # DEBUG = False Errors just show a plain, generic error page with none of that detail, because a live app shouldn't hand debugging information to random visitors.

            if target.id == "DEBUG":
                if isinstance (node.value, ast.Constant) and node.value.value is True: #if DEBUG = True defined on settings.py. When an error happens, it will display the traceback error details. 
                    #Revealing revealing CMS structure and DB schema to any visitor.

                    findings.append(Finding( #Append finding to main class findings
                        #Details from class (according also to rules matrix documentation on excel)
                        rule_id="SEC-MISCONFIG-DEBUG",
                        severity ="Critical",
                        attack_type_exposure="Stack Trace Exposure",
                        file_path=filepath, 
                        line=node.lineno,
                        message="DEBUG is set to True. In production this exposes detailed error tracebacks — including internal file paths and code structure — to any visitor.",
                        standard_ref= "OWASP Top 10:2025 A02 – Security Misconfiguration", #Standard name from OWASP matrix documentation
                    ))

            # --- RULE 2 Attack type Security misconfiguration — SECRET_KEY ---
            # Attack type covered: cryptographic key exposure — enabling session/token forgery.

            # Notes:
            # SECRET_KEY is used internally by Django to cryptographically sign things —session cookies, password-reset tokens, CSRF tokens. If an attacker learns
            # this value, they can forge any of those (e.g. a fake "logged in as admin" session) without ever needing a real password.
            
            # This rule flags SECRET_KEY whenever it's hardcoded directly in the source —
            # unsafe because it's committed to version control and can't differ between
            # environments. The safe pattern loads it from an environment variable at
            # runtime instead (e.g. os.environ.get("SECRET_KEY")), which this rule ignores.
            
            
            if target.id == "SECRET_KEY":
                #Shape A: harcoded directly as a string (SECRET_KEY = "abcd123")
                # Constant = a literal value written directly in the code.
                # isinstance(..., str) narrows it to strings specifically, since constant also covers True/False/numbers.
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    findings.append(Finding(
                         rule_id="SEC-MISCONFIG-SECRET-KEY",
                         severity="Critical",
                         attack_type_exposure="Session/Cookie Forgery",
                         file_path=filepath,
                         line=node.lineno,
                         message="SECRET_KEY is a hardcoded string literal instead of being loaded from the environment.",
                         standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",  # Standard name from OWASP matrix documentation
                     ))
              
            # ---RULE 3 Attack type Security misconfiguration — ALLOWED_HOST ---
            # Attack type covered: Host header injection — allowing any host to connect.
            if target.id == "ALLOWED_HOSTS":
                # This condition only runs if the value is a list literal at all,
                # e.g. [] or ['*', 'example.com'] — not a variable or function call.
                if isinstance(node.value, ast.List):
                    # Condition 1 — is the list completely empty?
                    # len(node.value.elts) counts how many items are inside the list.
                    # If it's 0, ALLOWED_HOSTS was left blank.
                    if len(node.value.elts) == 0:
                        findings.append(Finding(
                            rule_id="SEC-MISCONFIG-ALLOWED-HOSTS-EMPTY",
                            severity="Critical",
                            attack_type_exposure="Host Header Injection",
                            file_path=filepath,
                            line=node.lineno,
                            message="ALLOWED_HOSTS is empty.",
                            standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",
                        ))
                    else:
                        # Condition 2 — the list has items, so check each one individually
                        # to see if the wildcard '*' is hiding among them.
                        for elt in node.value.elts:
                            # isinstance(elt, ast.Constant) confirms this item is a plain
                            # literal value (like a string), not a variable or expression.
                            # elt.value == "*" then checks if that literal is specifically
                            # the wildcard character.
                            if isinstance(elt, ast.Constant) and elt.value == "*":
                                findings.append(Finding(
                                    rule_id="SEC-MISCONFIG-ALLOWED-HOSTS-WILDCARD",
                                    severity="Critical",
                                    attack_type_exposure="Host Header Injection",
                                    file_path=filepath,
                                    line=node.lineno,
                                    message="ALLOWED_HOSTS contains '*', allowing any host.",
                                    standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",
                                ))

                        #Condition 3 - dynamic ALLOWED_HOSTS dynamic construction check
                elif isinstance (node.value, ast.ListComp):
                    findings.append(Finding(
                         rule_id="SEC-MISCONFIG-ALLOWED-HOSTS-DYNAMIC",
                         severity="Medium",
                         attack_type_exposure="Host Header Injection",
                         file_path=filepath,
                         line=node.lineno,
                         message=(
                             "ALLOWED_HOSTS is built dynamically (e.g. via a list comprehension "
                             "over an environment variable) rather than as a plain list literal. "
                             "This rule cannot verify what value it actually resolves to without "
                             "running the code, so a dangerous default hidden inside the "
                             "expression — e.g. os.getenv('ALLOWED_HOSTS', '*') falling back to "
                             "a wildcard if the environment variable is unset — would go "
                             "completely undetected. Manually confirm the fallback value used "
                             "here is a safe, explicit domain list, not an empty string or '*'."
                        ),
                        standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",
        ))
    
                                     
# ---RULE 4: Security misconfiguration - missing SSL/HSTS ---
    #Only applies to settings.py 
    # Presence check only (Django doesn't enable these by default, and the 
    # value could come from an env var I can't verify statically (needs manual review)
    #Attack type covered: Man in the middle attack (MITM) through SSL-Stripping, attack that
    #forces a target's browser to downgrade from HTTPS (encrypted) to HTTP (unencrypted)
    #traffic and session cookies (e.g. CMS admin login) can be intercepted

    #Django does not enable this HTTPS enforcement by default - both settings must be explicitly added.
    #this is a PRESENCE check, not a value check:
    #we're only asking "were these names ever assigned at all?", not what
    #they equal, since the actual value could come from an env var or a
    #conditional that can't be verified statically
    if filepath.endswith("settings.py"):
        missing_ssl_keys = []
        if "SECURE_SSL_REDIRECT" not in assigned_names:
            missing_ssl_keys.append("SECURE_SSL_REDIRECT")
        if "SECURE_HSTS_SECONDS" not in assigned_names:
            missing_ssl_keys.append("SECURE_HSTS_SECONDS")

        if missing_ssl_keys:
            findings.append(Finding(
                rule_id="SEC-MISCONFIG-SSL-HSTS-MISSING",
                severity="Critical",
                attack_type_exposure="SSL Stripping (Man-in-the-Middle)",
                file_path=filepath,
                #I put 1 here on purpose. It's not a real line number — this rule is about something missing, and missing things don't have a line
                line=1,
                message=(
                    f"Missing HTTPS enforcement settings(s): {', '.join(missing_ssl_keys)}. "
                    "Without these, traffic and session cookies (e.g. CMS admin login) can be "
                    "intercepted via SSL stripping / man-in-the-middle attacks. Add "
                    "SECURE_SSL_REDIRECT = True and SECURE_HSTS_SECONDS = 31536000."
                ),
                standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",
            ))
    return findings 

#---RULE 5 SEC-MISCONFIG-HARDCODED-SECRET---
#Variable names that typically hold secrets. If any of these is assigned
#a hardcoded string instead of being kept secret.
SECRET_NAME_PATTERNS = ("SECRET", "PASSWORD", "API_KEY", "TOKEN", "PRIVATE_KEY")

def check_hardcoded_secrets(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            #Check if the variable name looks secret-like(SECRET_KEY, API_KEY, DB_PASSWORD, etc.)
            name_upper = target.id.upper()
            if not any(pattern in name_upper for pattern in SECRET_NAME_PATTERNS):
                continue
            #Only flag if the VALUE is a hardcoded string literal — if it's
            #.env that's the safe pattern already covered by ENV_FALLBACK_WATCHLIST.
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
                findings.append(Finding(
                    rule_id="SEC-MISCONFIG-HARDCODED-SECRET",
                    severity="High",
                    attack_type_exposure="Credential Exposure",
                    file_path=filepath,
                    line=node.lineno,
                    message=f"{target.id} is a hardcoded secret-like value in source code. Anyone with repo access can read it. Move it to .env and load it via os.environ.get('{target.id}').",
                    standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",
                ))

    return findings

                #---TIER 2 START ----

#---RULE 6 DANGEROUS CALLS - eval() / exec () ----
#looks for dangerous call names eval() / exec ()that the attacker can use as 
#and pass it as code, if that string ever comes from user input the attacker can run their own code on our server 
#(Read files, access the database, anything python can do)
DANGEROUS_CALL_NAMES = ("eval", "exec")

def check_unsafe_eval_exec(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        #Only care about function CALL nodes — e.g. eval(x), not just the word eval
        if not isinstance(node, ast.Call):
            continue

        #The function being called must be a plain name (not something.eval())
        if not isinstance(node.func, ast.Name):
            continue

        #Is this call to eval or exec specifically?
        if node.func.id in DANGEROUS_CALL_NAMES:
            findings.append(Finding(
                rule_id="SEC-UNSAFE-EVAL-EXEC",
                severity="Critical",
                attack_type_exposure="Arbitrary Code Execution",
                file_path=filepath,
                line=node.lineno,
                message=f"Call to {node.func.id}() found. If any part of its input comes from user data, this allows arbitrary code execution. Avoid eval/exec entirely, or use ast.literal_eval() for safe data parsing.",
                standard_ref="OWASP Top 10:2025 A03 – Injection",
            ))

    return findings

# ---RULE 7 DANGEROUS_DESERIALIZE_CALLS pickle.loads ---

#Looks for pickle.loads() calls — pickle doesn't just read data, it can
#reconstruct and RUN arbitrary Python objects from the bytes it's given.
#If the argument comes from outside the code (request data, cache, file
#upload) instead of a hardcoded literal, an attacker can craft a payload
#that executes their own code the moment it's loaded.
DANGEROUS_DESERIALIZE_CALLS = ("loads", "load")

def check_insecure_deserialization(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        #Only care about function CALL nodes
        if not isinstance(node, ast.Call):
            continue

        #We're looking for pickle.loads(...) or pickle.load(...) —
        #that's an Attribute access (pickle.something), not a plain Name
        if not isinstance(node.func, ast.Attribute):
            continue

        #Confirm the object being called on is literally named "pickle"
        #(pickle.loads), and the method is loads/load specifically
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "pickle":
            continue
        if node.func.attr not in DANGEROUS_DESERIALIZE_CALLS:
            continue

        #No arguments at all — nothing to check, skip
        if not node.args:
            continue

        first_arg = node.args[0]

        #LIGHT TAINT CHECK: is the argument a hardcoded literal (safe,
        #e.g. pickle.loads(b"...")) or anything else (a variable, a
        #function call, request.body, etc — unknown origin, flag it)?
        if isinstance(first_arg, ast.Constant):
            continue  #True Negative don't create an issue, literal data, not attacker-controlled

        findings.append(Finding(
            rule_id="SEC-INSECURE-DESERIALIZATION-PICKLE",
            severity="Medium",
            attack_type_exposure="Remote Code Execution (Insecure Deserialization)",
            file_path=filepath,
            line=node.lineno,
            message=f"pickle.{node.func.attr}() is called with a non-literal argument. If this data crosses a trust boundary (request body, cache, file upload), a crafted payload can achieve remote code execution. Replace pickle with json for any data from outside the code.",
            standard_ref="OWASP Top 10:2025 A08 – Software or Data Integrity Failures",
        ))

    return findings

#---RULE 8 WEAK HASHING - hashlib.md5() / hashlib.sha1() ----
#Why these 2 on specific?  these 2 hashes techniques broken & depreceated by OWASP 
# algorithms still built intoy python standard library,and which are still commonly used

WEAK_HASH_ALGORITHMS = ("md5", "sha1")

def check_weak_hashing(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        #Only care about function CALL nodes
        if not isinstance(node, ast.Call):
            continue

        #looking for hashlib.md5(...) or hashlib.sha1(...) —
        #that's an Attribute access (hashlib.something), not a plain Name
        if not isinstance(node.func, ast.Attribute):
            continue

        #Comfirm the object being called on is named "hashlib"
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "hashlib":
            continue

        #Is this call to md5 or sha1 specifically?
        if node.func.attr in WEAK_HASH_ALGORITHMS:
            findings.append(Finding(
                rule_id="SEC-WEAK-HASHING-ALGORITHM",
                severity="Medium",
                attack_type_exposure="Cryptographic Weakness",
                file_path=filepath,
                line=node.lineno,
                message=f"hashlib.{node.func.attr}() is a broken hashing algorithm — collisions can be crafted deliberately. Use hashlib.sha256() or stronger. For passwords specifically, use Django's built-in make_password() (Argon2/PBKDF2) instead of manual hashing.",
                standard_ref="OWASP Top 10:2025 A04 – Cryptographic Failures",
            ))

    return findings

#---RULE 9 UNSAFE IMAGE UPLOAD - Image.open() on request.FILES ---

#Looks for image.open() called directly on request.FILES with no validation first

#A crafted image (image modified by an attacher that can be visualized normally but the internal gygabites structure is modified)
# when decode it into gygabites of pixel data (decompression bomb) or trigger a known 
# CVE- (common vulnerability exposure in third libraries used in python) 
# the attacker con exploit the attack techniques exhausting server memory(CPU) 

def check_unsafe_image_upload(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        #Only care about function CALL nodes
        if not isinstance(node, ast.Call):
            continue

        #Looking for Image.open(...) — that's an Attribute access
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "open":
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "Image":
            continue

        #No arguments — nothing to check
        if not node.args:
            continue

        first_arg = node.args[0]

        #Convert the argument to source-like text so I can check if it
        #mentions "request.FILES" — a simple text check, not full taint
        #tracing, but enough to catch the direct/unvalidated case.
        arg_text = ast.dump(first_arg)
        if "FILES" not in arg_text:
            continue  #not an upload — not what this rule cares about

        findings.append(Finding(
            rule_id="SEC-UNSAFE-IMAGE-UPLOAD",
            severity="Medium",
            attack_type_exposure="Denial of Service (Decompression Bomb)",
            file_path=filepath,
            line=node.lineno,
            message="Image.open() is called directly on request.FILES with no visible validation. A crafted image can trigger a decompression bomb or exploit a known Pillow vulnerability. Validate file size, MIME type, and dimensions before processing, and set Image.MAX_IMAGE_PIXELS.",
            standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration / A05 – Injection",
        ))

    return findings

#---TIER 2/3 - call-pattern + string content check (does the regex literal contain a nested quantifier?)---

#---RULE 10 ReDoS - UNSAFE REGEX PATTERNS ----

# REGEX definition = python regular expression is a pattern-matching lenguage
#SHAPES of text, not exact fixed strings  

#Looks for re.compile()/re.match()/re.search() calls where the pattern
#contains a NESTED QUANTIFIER shape — e.g. (a+)+ or (a*)*. These cause
#catastrophic backtracking: a CRAFTED input string (deliberately built
#by an attacker) can make matching time explode exponentially, freezing
#a worker and exhausting the whole worker pool (DoS).
#Pool of workers - server application server available to handle requests

#Note: the danger is in the PATTERN (code I wrote), not the runtime
#input — this rule only sees the pattern, since that's what's in source.

import re as re_module  #aliased so it doesn't collide with the "re" i'm scanning FOR

REGEX_CALL_NAMES = ("compile", "match", "search", "fullmatch")

#A lightweight, deliberately simple detector for the classic nested-
#quantifier shape: a group containing a quantifier, itself followed by
#another quantifier — e.g. (a+)+, (a*)*, (a|aa)+. Not a full analysis,
#just a pattern match over the regex text itself.
NESTED_QUANTIFIER_SHAPE = re_module.compile(r"\([^()]*[+*][^()]*\)[+*]")

def check_redos_unsafe_regex(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        #Only care about function CALL nodes
        if not isinstance(node, ast.Call):
            continue

        #Looking for re.compile(...) / re.match(...) / re.search(...) /
        #re.fullmatch(...) — Attribute access, object literally named "re"
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "re":
            continue
        if node.func.attr not in REGEX_CALL_NAMES:
            continue

        #No arguments — nothing to check
        if not node.args:
            continue

        first_arg = node.args[0]

        #Only useful if the pattern is a hardcoded string literal — if
        #it's a variable, I can't see its actual text at scan time.
        if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
            continue

        pattern_text = first_arg.value

        #Does the pattern's own text contain the dangerous nested-
        #quantifier shape?
        if NESTED_QUANTIFIER_SHAPE.search(pattern_text):
            findings.append(Finding(
                rule_id="SEC-REDOS-UNSAFE-REGEX",
                severity="Medium",
                attack_type_exposure="CPU Exhaustion (ReDoS)",
                file_path=filepath,
                line=node.lineno,
                message=f"re.{node.func.attr}() uses a pattern with nested quantifiers, vulnerable to catastrophic backtracking. A crafted input string can freeze this worker for minutes, and repeated requests can exhaust the whole worker pool (denial of service). Avoid nested quantifiers; use bounded quantifiers with a fixed max length.",
                standard_ref="CWE-1333 – Inefficient Regular Expression Complexity",
            ))

    return findings

#---RULE 11 RESOURCE STARVATION - MISSING TIMEOUTS / UNCLOSED RESOURCES ----

#Two related checks: (1) outbound HTTP calls with no timeout= can hang
#forever if the remote server never responds, tying up a worker
#indefinitely; (2) file handles/DB cursors/sockets opened without a
#"with" block can leak if an exception happens before .close() runs.
#Both slowly exhaust a limited resource pool (workers, file handles,
#DB connections) under repeated/parallel requests — same DoS family
#as ReDoS, but starving CONNECTIONS/WORKERS instead of CPU.

HTTP_CALL_METHODS = ("get", "post", "put", "delete", "patch", "head")

def check_missing_timeout(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        #Looking for requests.get(...) / requests.post(...) etc —
        #Attribute access, object literally named "requests"
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "requests":
            continue
        if node.func.attr not in HTTP_CALL_METHODS:
            continue

        #Check the KEYWORD arguments for timeout= — node.keywords is a
        #list of ast.keyword nodes, each with a .arg (the name) and
        #.value (what it's set to). I just need to know if "timeout"
        #was passed at all — not checking what value it's set to.
        has_timeout = any(kw.arg == "timeout" for kw in node.keywords)

        if not has_timeout:
            findings.append(Finding(
                rule_id="SEC-MISSING-TIMEOUT",
                severity="High",
                attack_type_exposure="Worker/Connection Pool Exhaustion",
                file_path=filepath,
                line=node.lineno,
                message=f"requests.{node.func.attr}() is called with no timeout= argument. If the remote server never responds, this call hangs forever, tying up a worker indefinitely. Repeated hangs exhaust the whole worker pool. Always pass an explicit timeout=.",
                standard_ref="CWE-400 – Uncontrolled Resource Consumption",
            ))

    return findings

#---RULE 12 SILENT FAIL-OPEN -BARE/ EMTPY EXCEPT ---

#Silent Fail-Open — an error is caught but silently ignored (except: pass), so the code continues as if nothing went wrong.
# If this happens during a permission check or validation, the request proceeds as if it succeeded — an attacker who triggers the error gets treated as authorized by accident.

#New AST node type: ast.ExceptHandler

def check_silent_fail_open(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        #Looking for an "except ...:" block specifically 
        if not isinstance(node, ast.ExceptHandler):
            continue

        #Is this a bare "except:" with no error type at all?
        is_bare_except = node.type is None

        #Or does it say "except Exception:" — still catches almost
        #everything, just slightly less extreme than fully bare
        is_broad_exception = (
            isinstance(node.type, ast.Name) and node.type.id == "Exception"
        )

        #If it catches a SPECIFIC error type instead, skip it — that's fine
        if not (is_bare_except or is_broad_exception):
            continue

        #Now check what's INSIDE the except block — is it just "pass",
        #meaning it does nothing at all with the error?
        body_is_noop = (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Pass)
        )

        #If it does something (logs, re-raises, returns an error), skip it
        if not body_is_noop:
            continue

        findings.append(Finding(
            rule_id="SEC-SILENT-FAIL-OPEN",
            severity="Medium",
            attack_type_exposure="Silent Fail-Open",
            file_path=filepath,
            line=node.lineno,
            message="This except block silently swallows the error with no logging or handling. If this wraps a permission check, validation, or moderation step, the request continues as if it succeeded even though it failed. Catch specific exception types, log the error, and fail closed (deny/return an error).",
            standard_ref="OWASP Top 10:2025 A10 – Mishandling of Exceptional Conditions",
        ))

    return findings

#---RULE 13 SQL INJECTION via String Concatenation ---
#SQL Injection via String Concatenation (most common form) — a code-
#level flaw where a query string is built by GLUING (concatenation) user input directly
#into SQL text, instead of using a parameterized placeholder.

#Example: login bypass
#  Intended (NOT parameterized):
#    SELECT * FROM users WHERE username='USER_INPUT' AND password='PASS';
#  Attacker enters into username: admin' --
#  Because the string was built via concatenation in OUR CODE (not the
#  database), the final string sent becomes:
#    SELECT * FROM users WHERE username='admin' --' AND password='...';
#  Everything after -- is a SQL comment, so the password check never
#  runs — attacker logs in as admin with no valid password.
#  (Login bypass is just ONE outcome — the same flaw can also read,
#  modify, or delete data across the whole database.)

#Looks for cursor.execute() calls where the query string is BUILT at
#runtime via string concatenation (+) or an f-string, instead of being
#a safe literal with placeholders. If any part of that built string
#comes from user input, an attacker can inject their own SQL.

#Prevention: parameterized queries (%s placeholders + a separate params
#list) — this is exactly what this rule checks FOR the absence of.

def check_sql_injection(tree, filepath):
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        #Looking for cursor.execute(...) — Attribute access ending in
        #"execute"(METHOD)
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "execute":
            continue

        if not node.args:
            continue

        query_arg = node.args[0]

        #DANGER SHAPE 1: an f-string. In the AST, f-strings become a
        #JoinedStr node — a mix of literal text pieces AND embedded
        #expressions (the {variable} parts). Any JoinedStr means a
        #variable got glued directly into the query text.
        is_fstring = isinstance(query_arg, ast.JoinedStr)

        #DANGER SHAPE 2: string concatenation or % formatting, e.g.
        #"SELECT * WHERE id=" + tip_id, or "...%s" % tip_id. In the
        #AST, both + and % both are the same danger shape here.
        is_binop_built = isinstance(query_arg, ast.BinOp)

        if not (is_fstring or is_binop_built):
            continue  #plain string literal or %s-placeholder call — safe, skip

        findings.append(Finding(
            rule_id="SEC-SQL-INJECTION",
            severity="Critical",
            attack_type_exposure="SQL Injection",
            file_path=filepath,
            line=node.lineno,
            message="cursor.execute() is called with a query string built via f-string or concatenation instead of a parameterised placeholder. If any part of this string comes from user input, an attacker can inject arbitrary SQL, risking full database exfiltration or authentication bypass. Use %s placeholders with a separate params list instead.",
            standard_ref="OWASP Top 10:2025 A05 – Injection",
        ))

    return findings

