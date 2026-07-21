"""SAST (Static Application Security Testing (analysis of the application's own source code) 
via AST parsing (Abstract Syntax Tree) it reads the code the way python itself understands it - as structure, not text. Every piece of code becomes a "node" in a tree"""

#Import findings file from main class 
from scanner.findings import Finding
#AST module for Abstract Syntax Tree functionality
import ast

# For every rule, there is one function assign to the main class (findings)

# ---RULE 1---
# Attack type Security misconfiguration — DEBUG/SECRET_KEY/ALLOWED_HOSTS

#Parameter tree as type ast.AST
#Parameter filepath as type str
def check_security_misconfig(tree: ast.AST, filepath: str) -> list [Finding]: #-> this function will return a list of finding objects
    findings = [] #Empty list which the function will fill up as it walks the three and returns at the end. 

#ast.walk(tree) visit every single node in the whole three. Every function, imports, if-statements, etc.
#The "node" variable becomes each of thise per iteration is a loop for every node in the code.
    for node in ast.walk (tree):
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

            #---1. DEBUG check---
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
                        file_path=filepath, 
                        line=node.lineno,
                        message="DEBUG is set to True. In production this exposes detailed error tracebacks — including internal file paths and code structure — to any visitor.",
                        standard_ref= "OWASP Top 10:2025 A02 – Security Misconfiguration", #Standard name from OWASP matrix documentation
                    ))
            # --- 2. SECRET_KEY check ---
            # Attack type covered: cryptographic key exposure — enabling session/token forgery.

            # Notes:
            # SECRET_KEY is used internally by Django to cryptographically sign things —session cookies, password-reset tokens, CSRF tokens. If an attacker learns
            # this value, they can forge any of those (e.g. a fake "logged in as admin" session) without ever needing a real password.
            
            # This rule flags SECRET_KEY whenever it's hardcoded directly in the source —
            # unsafe because it's committed to version control and can't differ between
            # environments. The safe pattern loads it from an environment variable at
            # runtime instead (e.g. os.environ.get("SECRET_KEY")), which this rule ignores.
            
            
            if target.id == "SECRET_KEY":
                # Constant = a literal value written directly in the code.
                # isinstance(..., str) narrows it to strings specifically, since
                # Constant also covers True/False/numbers.
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    findings.append(Finding(
                        rule_id="SEC-MISCONFIG-SECRET-KEY",
                        severity="Critical",
                        file_path=filepath,
                        line=node.lineno,
                        message="SECRET_KEY is a hardcoded string literal instead of being loaded from the environment.",
                        standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",  # Standard name from OWASP matrix documentation
                    ))
            
            # --- 3. ALLOWED_HOSTS check ---
            # Attack type covered: Host header injection — allowing any host to connect.

            # Notes:
            # ALLOWED_HOSTS is a setting in settings.py that tells Django which domain names are allowed to serve this app. It has two unsafe states this rule watches for:
            # • ALLOWED_HOSTS = [] (empty) — with DEBUG=True this blocks every request,
            #   but developers often "fix" this in a hurry by pasting '*' in without
            #   thinking about what that actually allows.
            # • ALLOWED_HOSTS = ['*'] (wildcard) — this tells Django to accept a request
            #   claiming to be ANY domain name at all, via the Host header. Django trusts
            #   this value when generating absolute URLs (e.g. links in notifications,
            #   admin pages) or when caching responses. A malicious Host header can then
            #   cause the app to generate or cache content pointing at an attacker's domain
            #   instead of the real one — independent of whether the app itself uses
            #   passwords or logins.
            #
            
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
                                    file_path=filepath,
                                    line=node.lineno,
                                    message="ALLOWED_HOSTS contains '*', allowing any host.",
                                    standard_ref="OWASP Top 10:2025 A02 – Security Misconfiguration",
                                ))
    return findings