import sys
import os
import argparse
from io import StringIO
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.cli.parser_factory import create_parser

def test_cli_sync():
    print("🔍 Auditing CLI Command Synchronization...")
    parser = create_parser(invoked_as="yamlr")
    
    # Get all subcommands
    subparsers_actions = [
        action for action in parser._actions 
        if isinstance(action, argparse._SubParsersAction)
    ]
    
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
    help_commands = re.findall(r'\"([a-z0-9_-]+)\": lambda', content)
    print(f"Detected {len(help_commands)} help handlers: {', '.join(sorted(help_commands))}")

    missing_help = []
    for cmd in commands:
        if cmd not in help_commands:
            missing_help.append(cmd)
            print(f"❌ [MISSING HELP] Command '{cmd}' has no logic in help_formatter.py dispatch.")
        else:
            print(f"✅ [OK] Command '{cmd}' is synchronized.")

    if missing_help:
        print(f"\n🚨 FOUND {len(missing_help)} SYNCHRONIZATION ERRORS.")
        sys.exit(1)
    else:
        print("\n✨ ALL COMMANDS ARE 100% SYNCHRONIZED.")

if __name__ == "__main__":
    test_cli_sync()
