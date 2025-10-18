"""npm script content linting and risk analysis."""

import re
from typing import Any


# Dangerous patterns to look for in npm scripts
DANGEROUS_PATTERNS = [
    (r"curl\s", "curl command (may download arbitrary code)"),
    (r"wget\s", "wget command (may download arbitrary code)"),
    (r"Invoke-WebRequest", "PowerShell web request (may download code)"),
    (r"powershell", "PowerShell execution"),
    (r"cmd\.exe", "Windows command execution"),
    (r"chmod\s+\+x", "Making files executable"),
    (r"base64\s+(-d|--decode)", "Base64 decoding (possible obfuscation)"),
    (r"\beval\s*\(", "eval() call (code execution)"),
    (r"node\s+-e", "Node inline code execution"),
    (r"GITHUB_TOKEN", "GitHub token access"),
    (r"SSH_", "SSH credential access"),
    (r"\.env", "Environment file access"),
    (r"\$\(curl", "Command substitution with curl"),
    (r"sh\s+-c", "Shell command execution"),
    (r"bash\s+-c", "Bash command execution"),
    (r"python\s+-c", "Python inline code execution"),
    (r"https?://[^\s]+\|\s*(sh|bash)", "Pipe to shell from web"),
]


def lint_scripts(scripts: dict[str, Any]) -> tuple[float, list[str]]:
    """Lint npm scripts for dangerous commands and patterns.
    
    Args:
        scripts: Dictionary of script names to script contents
        
    Returns:
        Tuple of (risk_score 0.0-1.0, list of reasons)
    """
    if not scripts or not isinstance(scripts, dict):
        return 0.0, []
    
    reasons = []
    hit_count = 0
    high_risk_scripts = {"install", "preinstall", "postinstall"}
    has_dangerous_lifecycle = False
    
    # Check each script for dangerous patterns
    for script_name, script_content in scripts.items():
        if not isinstance(script_content, str):
            continue
        
        # Track if dangerous patterns appear in lifecycle scripts
        is_lifecycle = script_name in high_risk_scripts
        
        for pattern, description in DANGEROUS_PATTERNS:
            if re.search(pattern, script_content, re.IGNORECASE):
                hit_count += 1
                suffix = " (in lifecycle script!)" if is_lifecycle else ""
                reasons.append(f"{description} in '{script_name}'{suffix}")
                
                if is_lifecycle:
                    has_dangerous_lifecycle = True
    
    # Compute risk score with diminishing returns
    # Base score from pattern matches (up to 0.6)
    base_score = min(0.6, hit_count * 0.15)
    
    # Bonus if dangerous patterns appear in lifecycle scripts (up to +0.4)
    if has_dangerous_lifecycle:
        base_score = min(1.0, base_score + 0.4)
        reasons.append("Dangerous patterns in install/preinstall/postinstall")
    # Smaller bonus for just having lifecycle scripts (up to +0.2)
    elif any(name in high_risk_scripts for name in scripts.keys()):
        base_score = min(1.0, base_score + 0.2)
        reasons.append("Has install/preinstall/postinstall scripts")
    
    return min(1.0, base_score), reasons


def extract_script_urls(scripts: dict[str, Any]) -> list[str]:
    """Extract URLs from script contents for further analysis.
    
    Args:
        scripts: Dictionary of script names to script contents
        
    Returns:
        List of URLs found in scripts
    """
    urls = []
    url_pattern = re.compile(r"https?://[^\s\"']+")
    
    for script_content in scripts.values():
        if isinstance(script_content, str):
            urls.extend(url_pattern.findall(script_content))
    
    return list(set(urls))  # Return unique URLs
