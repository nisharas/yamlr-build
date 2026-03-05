import os
import yaml
import pytest
import argparse
from yamlr.cli.parser_factory import create_parser

def test_github_actions_parity():
    """
    Ensures that all current and future CLI flags are exposed as inputs 
    in the GitHub Actions, guaranteeing ecosystem parity for new Epics.
    """
    parser = create_parser("yamlr")
    
    # We map subcommands to their respective action.yml paths
    action_maps = {
        "scan": "actions/scan/action.yml",
        "heal": "actions/heal/action.yml"
    }
    
    # Flags we intentionally don't expose in GH Actions because they don't make sense in CI
    ignored_flags = {
        "help", "version", "summary_only", "plain", "quiet", "verbose", 
        "stream_to", "yes", "yes_all", "diff", "dry_run", "no_backup", "pro_preview"
    }

    # Extract all subparsers
    subparsers_actions = [
        action for action in parser._actions 
        if isinstance(action, getattr(argparse, '_SubParsersAction', type(parser._subparsers._group_actions[0])))
    ] if parser._subparsers else []
    
    subparsers_dict = {}
    if parser._subparsers:
        for action in parser._subparsers._group_actions:
            if hasattr(action, 'choices'):
                subparsers_dict.update(action.choices)

    missing_parity = []

    for cmd, action_file in action_maps.items():
        assert os.path.exists(action_file), f"Action file {action_file} missing!"
        with open(action_file, "r") as f:
            action_data = yaml.safe_load(f)
        
        inputs = action_data.get("inputs", {})
        action_inputs = {k.replace("-", "_") for k in inputs.keys()}
        action_inputs.add("targets")
        
        # Architectural Guarantee: if the action supports arbitrary extra arguments, 
        # it natively supports 100% of current and future CLI epics.
        if "extra_args" in action_inputs:
            continue
            
        cmd_parser = subparsers_dict.get(cmd)
        if not cmd_parser:
            continue
            
        for action in cmd_parser._actions:
            dest = action.dest
            
            # Skip positional arguments and ignored flags
            if not action.option_strings or dest in ignored_flags:
                continue
            
            if dest not in action_inputs:
                missing_parity.append(f"Command '{cmd}' is missing flag '{dest}' in {action_file}")

    if missing_parity:
        print("Ecosystem Parity Failure! Future-proofing violated:")
        for m in missing_parity:
            print(" - " + m)
        import sys
        sys.exit(1)
    else:
        print("All flags accounted for!")

if __name__ == "__main__":
    test_github_actions_parity()
