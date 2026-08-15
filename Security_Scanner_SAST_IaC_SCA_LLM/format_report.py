"""
Formats scanner findings (with or without AI enrichment) as a report, 
suitable for posting as a Github PR comment
"""

def format_report_markdown (enriched_findings, files_scanned):
    """
    enriched_findings: the list returned by enrich_findings()
    (each has rule_id, severity, file_path, line, message, standard_ref,
    ai_explanation, ai_note/ai_model)
    
    files_scanned: int, how many files were scanned

    """
    #Building the report line by line, cleaner to read. 
    #Markdown syntax (##, **bold**, `code`, > blockquote, --- horizontal rule) — 
    #these are exactly what GitHub renders nicely when posted as a PR comment
    lines = []

    lines.append("## 🔎 Security Scanner Results")
    lines.append("")
    lines.append (f"Scanned **{files_scanned}** files.")


#Even when there are zero findings, 'if not' branch will show a 'no issues' message
#so the GitHub Actions step that reads this file doesnt fail with a missing-file error on a clean scan

    if not enriched_findings:
        lines.append("✅ No security issues found in the repository")
        #
        return "\n".join(lines)
    
    lines.append(f"**{len(enriched_findings)} issue(s) found:**")
    lines.append("")

    for item in enriched_findings:
        #Appending Rule ouptut format 
        lines.append(f"### [{item['severity']}] `{item['rule_id']}`")
        lines.append(f"**File:** `{item['file_path']}:{item['line']}`")
        lines.append(f"**Attack Technique:** {item['attack_technique']}")
        lines.append(f"**Standard:** {item['standard_ref']}")
        lines.append("")
        lines.append(f"> {item['message']}")
        lines.append("")

        if item.get ("ai_explanation"):
            lines.append(f"**AI Explanation** _(via {item['ai_model']})_:")
            lines.append(item["ai_explanation"])
        else:
            lines.append(f"_{item.get('ai_note', 'AI enrichment unavailable.')}_")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)