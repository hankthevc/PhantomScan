"""npm package script content analysis."""

import re
from typing import Any


# Dangerous command patterns that may indicate malicious behavior
DANGEROUS_PATTERNS = [
    # Network access & download tools
    (r'\bcurl\b', "Uses curl for network requests"),
    (r'\bwget\b', "Uses wget for downloads"),
    (r'\bInvoke-WebRequest\b', "Uses PowerShell web requests"),
    (r'\bInvoke-RestMethod\b', "Uses PowerShell REST calls"),
    
    # Shell execution
    (r'\bpowershell\b', "Executes PowerShell"),
    (r'\bcmd\.exe\b', "Executes cmd.exe"),
    (r'\bsh\s+-c\b', "Shell command execution"),
    (r'\bbash\s+-c\b', "Bash command execution"),
    
    # Permission changes
    (r'\bchmod\s+\+x\b', "Makes files executable"),
    (r'\bchmod\s+777\b', "Sets world-writable permissions"),
    
    # Encoding/obfuscation
    (r'\bbase64\b', "Base64 encoding/decoding"),
    (r'\beval\b', "Uses eval() for code execution"),
    (r'\bnode\s+-e\b', "Node.js inline code execution"),
    (r'\bnode\s+--eval\b', "Node.js eval flag"),
    
    # Sensitive environment variables
    (r'\bGITHUB_TOKEN\b', "Accesses GitHub token"),
    (r'\bNPM_TOKEN\b', "Accesses NPM token"),
    (r'\bSSH_[A-Z_]+\b', "Accesses SSH credentials"),
    (r'\.env\b', "References .env file"),
    (r'\bAWS_[A-Z_]+\b', "Accesses AWS credentials"),
    
    # File system manipulation
    (r'\brm\s+-rf\b', "Recursive force delete"),
    (r'\bdd\s+if=', "Disk duplication tool"),
    
    # Process injection
    (r'\bptrace\b', "Process tracing/injection"),
    (r'\bLD_PRELOAD\b', "Dynamic library injection"),
]


# Compile patterns once
COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in DANGEROUS_PATTERNS]


# Lifecycle scripts that run automatically during install
AUTO_RUN_SCRIPTS = {"install", "preinstall", "postinstall"}


def lint_scripts(scripts: dict[str, Any]) -> tuple[float, list[str]]:
    """Analyze npm scripts for suspicious patterns.

    Args:
        scripts: Dictionary of script names to commands

    Returns:
        Tuple of (risk_score, reasons)
        - risk_score: Float from 0.0 (safe) to 1.0 (high risk)
        - reasons: List of human-readable reasons
    """
    if not scripts or not isinstance(scripts, dict):
        return 0.0, []

    reasons: list[str] = []
    hit_count = 0
    has_auto_run = False

    # Check for auto-running scripts
    auto_run_found = set(scripts.keys()) & AUTO_RUN_SCRIPTS
    if auto_run_found:
        has_auto_run = True
        reasons.append(f"Has auto-run scripts: {', '.join(sorted(auto_run_found))}")

    # Scan each script for dangerous patterns
    matches_by_script: dict[str, list[str]] = {}
    
    for script_name, script_content in scripts.items():
        if not isinstance(script_content, str):
            continue
            
        script_matches = []
        for pattern, reason in COMPILED_PATTERNS:
            if pattern.search(script_content):
                hit_count += 1
                script_matches.append(reason)
        
        if script_matches:
            matches_by_script[script_name] = script_matches

    # Report matches grouped by script
    for script_name, matches in matches_by_script.items():
        unique_matches = sorted(set(matches))
        reasons.append(f"Script '{script_name}': {', '.join(unique_matches)}")

    # Compute risk score with diminishing returns
    # Base score from pattern hits (cap at 10 hits for 0.7)
    base_score = min(hit_count / 15.0, 0.7)
    
    # Boost significantly if auto-run scripts contain dangerous patterns
    if has_auto_run and hit_count > 0:
        # Auto-run scripts with dangerous patterns are very high risk
        base_score = min(base_score + 0.3, 1.0)
        reasons.append("⚠️ CRITICAL: Auto-run scripts contain dangerous patterns")
    elif has_auto_run:
        # Auto-run scripts alone are moderate risk
        base_score = max(base_score, 0.4)

    return min(base_score, 1.0), reasons
