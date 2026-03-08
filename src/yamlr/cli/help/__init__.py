"""
Yamlr CLI Help Package.

Why: Decomposed from monolithic help_formatter.py to enforce the
     500-line modularity limit. Each module handles a group of
     related commands.

Modules:
    help_scan.py     — scan, check, audit
    help_heal.py     — heal
    help_toolbox.py  — diagnose, secure, upgrade/migrate, dna, evidence
    help_utils.py    — catalog, version, explain, auth, init, restore,
                       demo, welcome, completion, status, rules, stats, manual
"""
