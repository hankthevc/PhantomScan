"""Utility functions for Streamlit webapp."""


def get_risk_level(score: float) -> tuple[str, str, str]:
    """Get risk level info based on score.
    
    Args:
        score: Risk score (0.0 - 1.0)
        
    Returns:
        Tuple of (level_name, emoji, css_class)
    """
    if score >= 0.8:
        return ("CRITICAL", "🔴", "critical")
    elif score >= 0.6:
        return ("HIGH", "🟠", "high")
    elif score >= 0.4:
        return ("MEDIUM", "🟡", "medium")
    else:
        return ("LOW", "🟢", "low")


def get_ecosystem_badge(ecosystem: str) -> str:
    """Get HTML badge for ecosystem.
    
    Args:
        ecosystem: Ecosystem name (pypi, npm)
        
    Returns:
        HTML badge string
    """
    icons = {
        "pypi": "🐍",
        "npm": "📦"
    }
    icon = icons.get(ecosystem.lower(), "📦")
    return f'<span class="ecosystem-badge ecosystem-{ecosystem.lower()}">{icon} {ecosystem.upper()}</span>'


def get_risk_badge(score: float) -> str:
    """Get HTML badge for risk score.
    
    Args:
        score: Risk score (0.0 - 1.0)
        
    Returns:
        HTML badge string
    """
    level, emoji, css_class = get_risk_level(score)
    return f'<span class="risk-badge-{css_class}">{emoji} {level}</span>'


def format_score_display(score: float) -> str:
    """Format score for display with color.
    
    Args:
        score: Risk score (0.0 - 1.0)
        
    Returns:
        Formatted score string with percentage
    """
    percentage = int(score * 100)
    return f"{score:.2f} ({percentage}%)"
