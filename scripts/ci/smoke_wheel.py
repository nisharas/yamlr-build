#!/usr/bin/env python3
"""Install a built Yamlr wheel and smoke-test its packaged CLI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path


def verify_wheel_layout(wheel: Path) -> None:
    """Reject native-only or accidentally archived distributions before install."""
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    required = {
        "yamlr/__init__.py",
        "yamlr/__main__.py",
        "yamlr/_find_bin.py",
        "yamlr_native/__init__.py",
    }
    missing = required - names
    if missing:
        raise ValueError(f"Wheel is missing supported package files: {sorted(missing)}")
    if not any(
        name.startswith("yamlr_native/yamlr_native") and name.endswith((".so", ".pyd"))
        for name in names
    ):
        raise ValueError("Wheel is missing its packaged native extension")
    if any(name.startswith(("yamlr/_archive/", "yamlr/pro/")) for name in names):
        raise ValueError("Wheel includes unsupported archived Python modules")


def run_checked(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Command failed with exit code {result.returncode}: {command!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel_directory", type=Path)
    parser.add_argument(
        "--native-bin",
        type=Path,
        help="Compare the installed wheel's isolated extension bridge with this standalone CLI",
    )
    parser.add_argument(
        "--license-texts",
        type=Path,
        help="Write installed Python dependency license texts to this file",
    )
    parser.add_argument(
        "--license-inventory",
        type=Path,
        help="Write a machine-readable JSON inventory of installed Python dependencies",
    )
    args = parser.parse_args()

    wheel_dir = args.wheel_directory.resolve()
    wheels = sorted(wheel_dir.glob("yamlr-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(
            f"Expected exactly one yamlr wheel in {wheel_dir}, found {len(wheels)}"
        )
    verify_wheel_layout(wheels[0])

    env = os.environ.copy()
    env["YAMLR_TELEMETRY"] = "off"
    env["CI"] = "true"
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.pop("YAMLR_BINARY", None)
    env.pop("YAMLR_FORCE_PYTHON", None)

    with tempfile.TemporaryDirectory(prefix="yamlr-wheel-smoke-") as temporary:
        workdir = Path(temporary)
        venv_dir = workdir / "venv"
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        venv_python = venv_dir / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        yamlr_command = venv_dir / (
            "Scripts/yamlr.exe" if os.name == "nt" else "bin/yamlr"
        )
        run_checked(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                str(wheels[0]),
            ],
            cwd=workdir,
            env=env,
        )

        # Prove imports resolve to this clean environment, not an editable source
        # checkout or a user-installed package. Isolated mode ignores PYTHONPATH.
        import_check = (
            "import sys, pathlib, yamlr, yamlr_native; "
            "root = pathlib.Path(sys.prefix).resolve(); "
            "assert pathlib.Path(yamlr.__file__).resolve().is_relative_to(root); "
            "assert pathlib.Path(yamlr_native.__file__).resolve().is_relative_to(root)"
        )
        run_checked([str(venv_python), "-I", "-c", import_check], cwd=workdir, env=env)

        version_output = run_checked(
            [str(yamlr_command), "version", "--json"],
            cwd=workdir,
            env=env,
        )
        version = json.loads(version_output)
        if not isinstance(version, dict) or not version.get("version"):
            raise SystemExit(
                "Installed wheel did not return structured version metadata"
            )

        manifest = workdir / "smoke.yaml"
        report = workdir / "report.json"
        manifest.write_text(
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: wheel-smoke\n",
            encoding="utf-8",
        )
        run_checked(
            [
                str(yamlr_command),
                "scan",
                str(manifest),
                "--output",
                "json",
                "--output-file",
                str(report),
                "--exit-zero",
            ],
            cwd=workdir,
            env=env,
        )
        scan_report = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(scan_report, dict):
            raise SystemExit("Installed wheel did not write a JSON scan report")

        api_smoke = (
            "from yamlr import HealResult, heal_yaml, scan_yaml; "
            "content = 'apiVersion: v1\\nkind: Pod\\nmetadata:\\n  name: wheel-smoke\\n'; "
            "healed = heal_yaml(content, k8s_version='1.30'); "
            "assert isinstance(healed, HealResult) and isinstance(healed.healed_yaml, str); "
            "report = scan_yaml(content, k8s_version='1.30'); "
            "assert isinstance(report, dict) and 'violations' in report and 'identity' in report"
        )
        run_checked([str(venv_python), "-I", "-c", api_smoke], cwd=workdir, env=env)

        if args.native_bin:
            native_bin = args.native_bin.resolve(strict=True)
            parity_runner = (
                Path(__file__).resolve().parents[2] / "tests" / "verify_rust_parity.py"
            )
            print(
                run_checked(
                    [
                        str(venv_python),
                        "-I",
                        str(parity_runner),
                        "--native-bin",
                        str(native_bin),
                    ],
                    cwd=workdir,
                    env=env,
                ).strip()
            )

        if args.license_texts or args.license_inventory:
            checker = shutil.which("pip-licenses")
            if checker is None:
                raise SystemExit(
                    "pip-licenses must be installed in the runner environment to generate license reports"
                )
            if args.license_texts:
                license_texts_path = args.license_texts.resolve()
                license_texts_path.parent.mkdir(parents=True, exist_ok=True)
                run_checked(
                    [
                        checker,
                        f"--python={venv_python}",
                        "--from=mixed",
                        "--format=plain-vertical",
                        "--with-license-file",
                        "--no-license-path",
                        f"--output-file={license_texts_path}",
                    ],
                    cwd=workdir,
                    env=env,
                )
            if args.license_inventory:
                license_inventory_path = args.license_inventory.resolve()
                license_inventory_path.parent.mkdir(parents=True, exist_ok=True)
                run_checked(
                    [
                        checker,
                        f"--python={venv_python}",
                        "--from=mixed",
                        "--format=json",
                        "--no-license-path",
                        f"--output-file={license_inventory_path}",
                    ],
                    cwd=workdir,
                    env=env,
                )
                try:
                    inventory = json.loads(
                        license_inventory_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError) as error:
                    raise SystemExit(
                        f"pip-licenses did not create a valid JSON inventory: {error}"
                    ) from error
                if not isinstance(inventory, list) or not inventory:
                    raise SystemExit(
                        "pip-licenses created an empty or invalid JSON inventory"
                    )

    print(f"Python wheel smoke passed: {wheels[0].name} ({version['version']})")


if __name__ == "__main__":
    main()
