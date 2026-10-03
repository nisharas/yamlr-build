"""Main CLI entry point for yamlr (Ruff Model).

Why: Delegates CLI commands to the native Rust binary or Rust extension. The
     Python API remains available independently through the PyO3 module.
"""

import os
import subprocess
import sys

from yamlr._find_bin import find_yamlr_bin


def cli() -> None:
    """Execute the yamlr CLI command line.

    Why: Prefers the standalone Rust binary, then uses the Rust extension
         shipped in the wheel. The archived Python CLI is a source-only
         compatibility path when explicitly requested.
    """
    force_python = os.environ.get("YAMLR_FORCE_PYTHON", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    if not force_python:
        bin_path = find_yamlr_bin()
        if bin_path:
            args = [bin_path] + sys.argv[1:]
            if sys.platform == "win32":
                try:
                    code = subprocess.call(args)
                    sys.exit(code)
                except KeyboardInterrupt:
                    sys.exit(130)
                return
            else:
                os.execv(bin_path, args)
                return

    if force_python:
        try:
            from yamlr.cli.main import main as py_main
        except ImportError as error:
            print(
                "[ERROR] The archived Python CLI is not included in this package. "
                "Unset YAMLR_FORCE_PYTHON to use the native CLI.",
                file=sys.stderr,
            )
            raise SystemExit(2) from error
        py_main()
        return

    try:
        from yamlr_native import native_cli_run
    except ImportError as error:
        print(
            "[ERROR] Yamlr's native CLI extension is unavailable. Reinstall the "
            "platform wheel or install the standalone yamlr binary.",
            file=sys.stderr,
        )
        raise SystemExit(2) from error

    raise SystemExit(native_cli_run(["yamlr", *sys.argv[1:]]))


if __name__ == "__main__":
    cli()
