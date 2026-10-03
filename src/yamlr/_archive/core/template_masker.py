"""In-memory Helm Go-template token masking and unmasking.

Enables Yamlr to scan and heal unrendered Helm chart templates without syntax
errors by temporarily masking Go template directives ({{ ... }}) into valid YAML
placeholders and restoring them bit-for-bit after analysis. Supports multiline
directives and control-flow blocks.
"""
import re
from typing import Dict, Tuple

# Regex matching Go template delimiters: {{ ... }} and {{- ... -}}, spanning newlines
GO_TEMPLATE_REGEX = re.compile(r"\{\{-?[\s\S]*?-?\}\}")


def mask_go_templates(content: str) -> Tuple[str, Dict[str, str]]:
    """Masks unrendered Go template directives into valid YAML tokens.

    Handles single-line and multiline Go template directives, distinguishing
    between line-level control flow blocks and inline key/value expressions.

    Args:
        content: Raw manifest or template content.

    Returns:
        A tuple of (masked_content, token_map).
    """
    token_map: Dict[str, str] = {}
    counter = 0

    new_parts = []
    last_idx = 0

    matches = list(GO_TEMPLATE_REGEX.finditer(content))
    for match in matches:
        start = match.start()
        end = match.end()
        raw_tag = match.group(0)

        line_start = content.rfind("\n", 0, start) + 1
        prefix = content[line_start:start]

        line_end = content.find("\n", end)
        if line_end == -1:
            line_end = len(content)
        suffix = content[end:line_end]

        # Check if this tag is a standalone control block on its own line(s)
        if prefix.strip() == "" and suffix.strip() == "":
            new_parts.append(content[last_idx:line_start])
            token_id = f"__YAMLR_TMPL_LINE_{counter}__"
            full_block = content[line_start:line_end]
            token_map[token_id] = full_block
            counter += 1
            indent = len(prefix)
            new_parts.append(f"{' ' * indent}# {token_id}")
            last_idx = line_end
        elif suffix.lstrip().startswith(":"):
            # Dynamic mapping key expression (e.g. {{ .Values.customKey }}: value)
            new_parts.append(content[last_idx:start])
            token_id = f"__YAMLR_TMPL_KEY_{counter}__"
            token_map[token_id] = raw_tag
            counter += 1
            new_parts.append(token_id)
            last_idx = end
        else:
            # Inline value tag (e.g. name: {{ .Release.Name }})
            new_parts.append(content[last_idx:start])
            token_id = f"__YAMLR_TMPL_VAL_{counter}__"
            token_map[token_id] = raw_tag
            counter += 1
            new_parts.append(token_id)
            last_idx = end

    new_parts.append(content[last_idx:])
    return "".join(new_parts), token_map


def unmask_go_templates(content: str, token_map: Dict[str, str]) -> str:
    """Restores masked Go template tokens back to their original text.

    Args:
        content: Masked or healed YAML content.
        token_map: Mapping of token IDs to original template directives.

    Returns:
        Content with original Go template directives restored bit-for-bit.
    """
    if not token_map:
        return content

    result = content

    # 1. Restore line-level control flow comments
    for token_id, original_line in token_map.items():
        if token_id.startswith("__YAMLR_TMPL_LINE_"):
            pattern = re.compile(rf"^[ \t]*#[ \t]*{re.escape(token_id)}", re.MULTILINE)
            result = pattern.sub(original_line, result)

    # 2. Restore inline template keys and values
    for token_id, original_tag in token_map.items():
        if token_id.startswith("__YAMLR_TMPL_KEY_") or token_id.startswith("__YAMLR_TMPL_VAL_"):
            result = result.replace(token_id, original_tag)

    return result
