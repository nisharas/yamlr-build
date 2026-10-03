//! Shell completion generator CLI handler.
//!
//! Why: Developer ergonomics are elevated when terminal tabs auto-complete
//! yamlr commands, subcommands, and flags directly in bash, zsh, fish, and PowerShell.

use crate::cli::{EXIT_SUCCESS, EXIT_USAGE};

/// Generates shell completion scripts for supported terminal shells.
///
/// Why: Provides seamless autocompletion of all 23+ commands and flags.
pub fn execute_completion(args: &[String]) -> i32 {
    let matches = match super::support_contract::parse("completion", args) {
        Ok(matches) => matches,
        Err(error) => return super::report_argument_error(error),
    };
    let shell = matches.get_one::<String>("shell").unwrap();

    match shell.as_str() {
        "bash" => {
            print!(
                "{}\n",
                r#"# yamlr bash completion
_yamlr() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="scan heal diff fmt fix check audit catalog doctor diagnose baseline init dna explain secure fleet rollback status evidence idp-export subscribe upgrade lsp mcp version help --k8s-version --output --apply --dry-run --fail-on --no-telemetry"
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}
complete -F _yamlr yamlr"#
            );
            EXIT_SUCCESS
        }
        "zsh" => {
            print!(
                "{}\n",
                r#"#compdef yamlr
_yamlr() {
    local -a commands
    commands=(
        'scan:Audit manifests for schema and integrity violations'
        'heal:Auto-remediate manifests with comment preservation'
        'diff:Preview unified diff of proposed fixes'
        'fmt:Canonical manifest formatting'
        'fix:Instant auto-repair'
        'check:Strict non-healing linter'
        'audit:Deep CIS benchmark compliance audit'
        'catalog:List active forensic detectors'
        'doctor:Validate engine and schema integrity'
        'diagnose:Verbose system diagnostics'
        'baseline:Snapshot or verify drift against baseline'
        'init:Initialize .yamlr.yaml configuration'
        'dna:Semantic fingerprinting'
        'explain:Explain rule rationale'
        'secure:Synthesize least-privilege NetworkPolicies'
        'fleet:Multi-repo GitOps batch remediation'
        'rollback:Restore from WAL journal'
        'status:Display workspace engine status'
        'evidence:Generate compliance evidence report'
        'idp-export:Export to Backstage or Port format'
        'version:Show version'
        'help:Show help'
    )
    _describe 'command' commands
}"#
            );
            EXIT_SUCCESS
        }
        "powershell" | "pwsh" => {
            print!(
                "{}\n",
                r#"Register-ArgumentCompleter -Native -CommandName yamlr -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @(
        'scan', 'heal', 'diff', 'fmt', 'fix', 'check', 'audit', 'catalog',
        'doctor', 'diagnose', 'baseline', 'init', 'dna', 'explain', 'secure',
        'fleet', 'rollback', 'status', 'evidence', 'idp-export', 'version', 'help'
    )
    $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}"#
            );
            EXIT_SUCCESS
        }
        "fish" => {
            print!(
                "{}\n",
                r#"complete -c yamlr -f -a "scan heal diff fmt fix check audit catalog doctor diagnose baseline init dna explain secure fleet rollback status evidence idp-export version help""#
            );
            EXIT_SUCCESS
        }
        _ => {
            eprintln!("Usage: yamlr completion <bash|zsh|fish|powershell>");
            EXIT_USAGE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_completion_shells() {
        assert_eq!(
            execute_completion(&[
                "yamlr".to_string(),
                "completion".to_string(),
                "bash".to_string()
            ]),
            EXIT_SUCCESS
        );
        assert_eq!(
            execute_completion(&[
                "yamlr".to_string(),
                "completion".to_string(),
                "zsh".to_string()
            ]),
            EXIT_SUCCESS
        );
        assert_eq!(
            execute_completion(&[
                "yamlr".to_string(),
                "completion".to_string(),
                "powershell".to_string()
            ]),
            EXIT_SUCCESS
        );
        assert_eq!(
            execute_completion(&[
                "yamlr".to_string(),
                "completion".to_string(),
                "fish".to_string()
            ]),
            EXIT_SUCCESS
        );
        assert_eq!(
            execute_completion(&[
                "yamlr".to_string(),
                "completion".to_string(),
                "unknown".to_string()
            ]),
            EXIT_USAGE
        );
    }
}
