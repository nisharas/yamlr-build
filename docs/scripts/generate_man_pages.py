import datetime
import os
import re
from pathlib import Path

# Constants for reuse and maintainability
RE_BOLD = r"\*\*([^*]+)\*\*"
RE_CODE = r"`([^`]+)`"
ROFF_BOLD = r"\\fB\1\\fR"

def _format_text(text):
    """Applies bold and code formatting for ROFF."""
    text = re.sub(RE_BOLD, ROFF_BOLD, text)
    text = re.sub(RE_CODE, ROFF_BOLD, text)
    return text

def _handle_code_block(lines, i):
    """Processes a Markdown code block into ROFF."""
    segment = ".nf\n.RS\n"
    i += 1
    while i < len(lines) and not lines[i].strip().startswith("```"):
        segment += lines[i] + "\n"
        i += 1
    segment += ".RE\n.fi\n"
    return segment, i

def _handle_block_elements(line):
    """Processes header, alert, and list elements into ROFF."""
    if line.startswith("## "):
        section = line[3:].strip().upper()
        return '.SH "SYNOPSIS"\n' if section == "USAGE" else f'.SH "{section}"\n'
    if line.startswith("### "):
        return f'.SS "{line[4:].strip()}"\n'
    if line.startswith("> [!"):
        return f'.IP "\\fB{line[4:-1].upper()}:\\fR" 4\n'
    if line.startswith("> "):
        return f'{_format_text(line[2:])}\n.PP\n'
    if line.startswith("* ") or line.startswith("- "):
        return f'.IP "\\(bu" 2\n{_format_text(line[2:])}\n'
    return None

def md_to_troff(markdown_text, command_name):
    """Converts a Markdown string to a ROFF man page."""
    date_str = datetime.datetime.now().strftime("%B %Y")
    troff = f'.TH "{command_name.upper()}" "1" "{date_str}" "Yamlr Manual" "User Commands"\n'
    troff += '.SH "NAME"\n'
    troff += f'{command_name} \\- Propose repairs and remediate Kubernetes manifests.\n'

    lines = markdown_text.splitlines()
    i = 0
    description_added = False
    
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("# "):
            i += 1
            continue

        if not description_added and not line.startswith("## "):
            troff += '.SH "DESCRIPTION"\n'
            description_added = True

        if line.startswith("```"):
            segment, i = _handle_code_block(lines, i)
            troff += segment
        else:
            segment = _handle_block_elements(line)
            if segment:
                troff += segment
            else:
                troff += f"{_format_text(line)}\n.PP\n"
        i += 1

    troff += '.SH "REPORTING BUGS"\n'
    troff += 'Report bugs to <https://github.com/yamlr/yamlr/issues>\n.PP\n'
    troff += '.SH "COPYRIGHT"\n'
    troff += 'Copyright \\(co 2026 Timonel Labs. Proprietary & Commercial Software (All Rights Reserved).\n'
    return troff

def generate_man_pages(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith(".md"):
            command_name = filename.replace("_", "-").replace(".md", "")
            with open(os.path.join(input_dir, filename), "r", encoding="utf-8") as f:
                troff_content = md_to_troff(f.read(), command_name)

            output_path = os.path.join(output_dir, f"{command_name}.1")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(troff_content)
            print(f"Generated {output_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent.parent
    generate_man_pages(str(base_dir / "docs/cli"), str(base_dir / "docs/man/man1"))
