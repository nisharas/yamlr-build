import argparse
import os
import sys
from io import StringIO
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.cli.parser_factory import create_parser


def test_cli_sync():
    print("AUDIT: Auditing CLI Command Synchronization...")
    parser = create_parser(invoked_as="yamlr")

    # Get all subcommands
    subparsers_actions = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]

    commands = []
    for action in subparsers_actions:
        # Compatibility for different argparse versions
        if hasattr(action, "choices"):
            commands.extend(action.choices.keys())
        elif hasattr(action, "_name_parser_map"):
            commands.extend(action._name_parser_map.keys())

    # Remove duplicates
    commands = sorted(list(set(commands)))

    print(f"Detected {len(commands)} subcommands: {', '.join(commands)}")

    # Extract help commands from help_formatter.py by reading the file
    help_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/yamlr/cli/help_formatter.py"))
    with open(help_file_path, "r") as f:
        content = f.read()

    # Look for keys in the 'dispatch' dict
    import re

    help_commands = re.findall(r"\"([a-z0-9_-]+)\": lambda", content)
    print(f"Detected {len(help_commands)} help handlers: {', '.join(sorted(help_commands))}")

    missing_help = []
    for cmd in commands:
        if cmd not in help_commands:
            missing_help.append(cmd)
            print(f"[MISSING HELP] Command '{cmd}' has no logic in help_formatter.py dispatch.")
        else:
            print(f"[OK] Command '{cmd}' is synchronized.")

    # Check for Markdown Manual Parity (docs/cli/)
    docs_cli_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../docs/cli"))
    missing_manuals = []
    
    for cmd in commands:
        # Normalize command name to file name (dashes to underscores)
        file_cmd = cmd.replace("-", "_")
        manual_path = os.path.join(docs_cli_dir, f"yamlr_{file_cmd}.md")
        
        if not os.path.exists(manual_path):
            missing_manuals.append(cmd)
            print(f"[MISSING MANUAL] Command '{cmd}' has no physical manual file at docs/cli/yamlr_{file_cmd}.md")
        else:
            print(f"[OK] Documentation file for '{cmd}' exists.")

    if missing_help or missing_manuals:
        print(f"\nERR: FOUND {len(missing_help)} HELP ERRORS AND {len(missing_manuals)} MANUAL ERRORS.")
        sys.exit(1)
    else:
        print("\nOK: ALL COMMANDS ARE 100% SYNCHRONIZED (HELP + MANUAL).")


if __name__ == "__main__":
    test_cli_sync()
