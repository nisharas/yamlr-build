#!/usr/bin/env python3
"""
Shared utilities for Formatter Report Mixins.
"""
from yamlr.cli.commands.base import get_console

def get_score_emoji(score: int) -> str:
    """Returns an emoji indicator based on health score."""
    if getattr(get_console(), "_yamlr_plain", False):
        if score >= 90: return "[v]"
        elif score >= 70: return "[!]"
        elif score >= 50: return "[?]"
        else: return "[x]"

    try:
        score_val = int(score)
    except (TypeError, ValueError):
        score_val = 0

    if score_val >= 90: return "🟢"
    elif score_val >= 70: return "🟡"
    elif score_val >= 50: return "🟠"
    else: return "🔴"

def get_icon_fallback(icon: str) -> str:
    """Returns ASCII fallback for emojis."""
    if not getattr(get_console(), "_yamlr_plain", False):
        return icon
    
    mapping = {
        "📊": "[#]", "✅": "[v]", "✓": "v", "→": "->", 
        "✎": "*", "⚠": "!", "○": "o", "↪": ">>", "✗": "x",
        "💾": "(B)", "✨": "OK", "💡": "i", "⚔️": "[!]",
        "⚠️": "!", "❌": "x", "🛡": "[S]", "📋": "[L]",
        "Reference:": "REF:"
    }
    return mapping.get(icon, icon)
