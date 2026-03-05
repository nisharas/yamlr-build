import os
import yaml
import argparse
from yamlr.cli.parser_factory import create_parser

def sync_actions():
    parser = create_parser("yamlr")
    
    action_maps = {
        "scan": "actions/scan",
        "heal": "actions/heal"
    }

    ignored_flags = {
        "help", "version", "summary_only", "plain", "quiet", "verbose", 
        "stream_to", "yes", "yes_all", "diff", "dry_run", "no_backup", "pro_preview", "targets"
    }

    sub = list({a.choices for a in parser._subparsers._group_actions if hasattr(a, 'choices')})[0] if parser._subparsers else {}

    for cmd, d_path in action_maps.items():
        yml_path = os.path.join(d_path, "action.yml")
        sh_path = os.path.join(d_path, "entrypoint.sh")
        
        with open(yml_path, "r") as f:
            action_data = yaml.safe_load(f)
            
        cmd_parser = sub.get(cmd)
        if not cmd_parser: continue

        inputs = action_data.setdefault("inputs", {})
        env_map = action_data.setdefault("runs", {}).setdefault("env", {})
        
        sh_lines = []
        with open(sh_path, "r") as f:
            sh_data = f.read()

        new_flags_bash = []

        for action in cmd_parser._actions:
            dest = action.dest
            if not action.option_strings or dest in ignored_flags:
                continue

            # Check if positional
            flag_name = action.option_strings[-1].lstrip("-")
            var_name = "INPUT_" + dest.upper()

            if flag_name not in inputs:
                inputs[flag_name] = {
                    "description": action.help or f"Corresponds to --{flag_name}",
                    "required": False
                }
                
                # If bool, true/false
                if isinstance(action, argparse._StoreTrueAction):
                    inputs[flag_name]["default"] = "false"
                    env_map[var_name] = "${{ inputs." + flag_name + " }}"
                    # Bash boolean injection
                    new_flags_bash.append(f'if [ "${{{var_name}:-false}}" = "true" ]; then CMD="$CMD --{flag_name}"; fi')
                else:
                    env_map[var_name] = "${{ inputs." + flag_name + " }}"
                    
                    if action.nargs == "?":
                        # Optional arg mapping
                        new_flags_bash.append(f'if [ "${var_name}" != "" ]; then if [ "${var_name}" = "*" ]; then CMD="$CMD --{flag_name}"; else CMD="$CMD --{flag_name} ${var_name}"; fi; fi')
                    else:
                        new_flags_bash.append(f'if [ -n "${var_name}" ]; then CMD="$CMD --{flag_name} ${var_name}"; fi')

        # Write action.yml
        class MyDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super(MyDumper, self).increase_indent(flow, False)
                
        with open(yml_path, "w") as f:
            yaml.dump(action_data, f, sort_keys=False, Dumper=MyDumper)
            
        # Append bash flags right before eval $CMD
        if new_flags_bash:
            inject_str = "\n".join(new_flags_bash) + "\n\n# Check for changes" if cmd == "heal" else "\n".join(new_flags_bash) + "\n\nexport GITHUB_TOKEN"
            
            if "eval $CMD" in sh_data:
                sh_data = sh_data.replace("eval $CMD", "\n".join(new_flags_bash) + "\n\neval $CMD")
            else:
                pass # Already handled manually inside script logic above
            
            with open(sh_path, "w", newline='\n') as f:
                f.write(sh_data)

if __name__ == "__main__":
    sync_actions()
    print("Sync complete.")
