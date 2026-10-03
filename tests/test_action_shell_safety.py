"""Regression checks for shell-safe GitHub Action input handling."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_scan_action_does_not_interpolate_inputs_into_shell():
    action_path = REPO_ROOT / ".github" / "actions" / "scan" / "action.yml"
    action = yaml.safe_load(action_path.read_text(encoding="utf-8"))
    step = next(
        item
        for item in action["runs"]["steps"]
        if item.get("name") == "Run Yamlr Scan"
    )

    assert step["env"] == {
        "YAMLR_SCAN_PATH": "${{ inputs.path }}",
        "YAMLR_SCAN_ARGS": "${{ inputs.args }}",
        "YAMLR_SCAN_SARIF_OUTPUT": "${{ inputs.sarif_output }}",
    }
    assert "${{ inputs." not in step["run"]
    assert 'yamlr scan "$YAMLR_SCAN_PATH"' in step["run"]
    assert '"${extra_args[@]}"' in step["run"]
    assert '"$YAMLR_SCAN_SARIF_OUTPUT"' in step["run"]
    assert "eval " not in step["run"]


def test_heal_action_passes_paths_and_extra_arguments_as_data():
    action_path = REPO_ROOT / ".github" / "actions" / "heal" / "action.yml"
    action = yaml.safe_load(action_path.read_text(encoding="utf-8"))
    step = next(
        item
        for item in action["runs"]["steps"]
        if item.get("name") == "Run Yamlr Heal"
    )

    assert step["env"] == {
        "YAMLR_HEAL_PATH": "${{ inputs.path }}",
        "YAMLR_HEAL_ARGS": "${{ inputs.args }}",
        "YAMLR_HEAL_APPLY": "${{ inputs.apply }}",
    }
    assert action["inputs"]["apply"]["default"] == "false"
    assert "Apply repairs to the workspace" in action["inputs"]["apply"]["description"]
    assert "${{ inputs." not in step["run"]
    assert 'yamlr heal "$YAMLR_HEAL_PATH"' in step["run"]
    assert 'apply_args+=(--apply)' in step["run"]
    assert '"${apply_args[@]}"' in step["run"]
    assert '"${extra_args[@]}"' in step["run"]
    assert "eval " not in step["run"]


def test_legacy_and_root_composite_actions_keep_inputs_out_of_shell_source():
    legacy_path = REPO_ROOT / ".github" / "actions" / "yamlr-scan" / "action.yml"
    legacy_action = yaml.safe_load(legacy_path.read_text(encoding="utf-8"))
    legacy_step = next(
        item
        for item in legacy_action["runs"]["steps"]
        if item.get("name") == "Run Audit"
    )

    assert legacy_step["env"]["YAMLR_SCAN_PATH"] == "${{ inputs.path }}"
    assert "${{ inputs." not in legacy_step["run"]
    assert '"$YAMLR_SCAN_PATH"' in legacy_step["run"]
    assert '"${command[@]}"' in legacy_step["run"]

    root_action = yaml.safe_load((REPO_ROOT / "action.yml").read_text(encoding="utf-8"))
    root_step = next(
        item
        for item in root_action["runs"]["steps"]
        if item.get("name") == "Execute Yamlr Engine"
    )

    assert root_step["env"]["YAMLR_PATH"] == "${{ inputs.path }}"
    assert root_step["env"]["YAMLR_COMMAND"] == "${{ inputs.command }}"
    assert "${{ inputs." not in root_step["run"]
    assert '"${COMMAND[@]}"' in root_step["run"]
    assert "eval " not in root_step["run"]


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bash") is None,
    reason="composite action integration test requires a POSIX Bash runner",
)
def test_root_action_forwards_crd_input_as_a_scan_argument(tmp_path):
    action = yaml.safe_load((REPO_ROOT / "action.yml").read_text(encoding="utf-8"))
    step = next(
        item
        for item in action["runs"]["steps"]
        if item.get("name") == "Execute Yamlr Engine"
    )
    assert step["env"]["YAMLR_CRD"] == "${{ inputs.crd }}"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture_file = tmp_path / "captured-args.json"
    yamlr_stub = bin_dir / "yamlr"
    yamlr_stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['YAMLR_CAPTURE_ARGS']).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n",
        encoding="utf-8",
    )
    yamlr_stub.chmod(0o755)

    manifest_path = str(tmp_path / "manifest with spaces.yaml")
    crd_path = str(tmp_path / "widget crd.yaml")
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
            "YAMLR_COMMAND": "scan",
            "YAMLR_PATH": manifest_path,
            "YAMLR_APPLY": "false",
            "YAMLR_WRITE": "false",
            "YAMLR_AUTOCOMMIT": "false",
            "YAMLR_CHECK": "false",
            "YAMLR_K8S_VERSION": "",
            "YAMLR_CRD": crd_path,
            "YAMLR_PUSH_TELEMETRY": "false",
            "YAMLR_CAPTURE_ARGS": str(capture_file),
        }
    )
    result = subprocess.run(
        [shutil.which("bash"), "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(capture_file.read_text(encoding="utf-8")) == [
        "scan",
        manifest_path,
        "--crd",
        crd_path,
    ]


def test_scan_and_heal_actions_run_the_checked_out_verifying_installer():
    for action_name in ("scan", "heal"):
        action_path = REPO_ROOT / ".github" / "actions" / action_name / "action.yml"
        action = yaml.safe_load(action_path.read_text(encoding="utf-8"))
        install_step = next(
            item
            for item in action["runs"]["steps"]
            if item.get("name") == "Install Standalone Yamlr Binary"
        )

        assert install_step["env"]["YAMLR_INSTALL_DIR"] == "${{ runner.temp }}/yamlr-bin"
        assert install_step["env"]["YAMLR_VERSION"] == "${{ inputs.version }}"
        assert install_step["env"]["YAMLR_VERIFY_ATTESTATION"] == "true"
        assert 'bash "$GITHUB_ACTION_PATH/../../../scripts/install.sh"' in install_step["run"]
        assert '"$YAMLR_INSTALL_DIR" >> "$GITHUB_PATH"' in install_step["run"]
        assert "command -v yamlr" not in install_step["run"]
        assert "curl " not in install_step["run"]
        assert "--no-verify" not in install_step["run"]


def test_installer_fails_closed_when_default_checksum_verification_cannot_run():
    installer = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")

    assert 'CHECKSUM_URL="${BASE_URL}/checksums.txt"' in installer
    assert 'awk -v asset="${ASSET_NAME}"' in installer
    assert "Refusing to install an unverified binary." in installer
    assert "Neither sha256sum nor shasum is available." in installer
    assert installer.index("Checksum verified:") < installer.index("Extracting release archive")


def test_legacy_and_root_actions_use_the_checked_out_installer_and_fail_visibly():
    legacy_path = REPO_ROOT / ".github" / "actions" / "yamlr-scan" / "action.yml"
    legacy_action = yaml.safe_load(legacy_path.read_text(encoding="utf-8"))
    legacy_install = next(
        item
        for item in legacy_action["runs"]["steps"]
        if item.get("name") == "Download Yamlr"
    )

    assert 'bash "$GITHUB_ACTION_PATH/../../../scripts/install.sh"' in legacy_install["run"]
    assert legacy_install["env"]["YAMLR_VERSION"] == "${{ inputs.version }}"
    assert legacy_install["env"]["YAMLR_VERIFY_ATTESTATION"] == "true"
    assert "curl " not in legacy_install["run"]
    assert "| sh" not in legacy_install["run"]

    root_action = yaml.safe_load((REPO_ROOT / "action.yml").read_text(encoding="utf-8"))
    root_install = next(
        item
        for item in root_action["runs"]["steps"]
        if item.get("name") == "Set up Yamlr Native Binary"
    )

    assert 'bash "$GITHUB_ACTION_PATH/scripts/install.sh"' in root_install["run"]
    assert root_install["env"]["YAMLR_VERSION"] == "${{ inputs.version }}"
    assert root_install["env"]["YAMLR_VERIFY_ATTESTATION"] == "true"
    assert "curl " not in root_install["run"]
    assert "| sh" not in root_install["run"]
    assert "Yamlr installation failed" in root_install["run"]
    assert "pip install \"$GITHUB_ACTION_PATH\"" in root_install["run"]


def test_release_installers_require_a_pinned_version_and_attested_archive():
    installer = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")

    assert 'VERSION="${YAMLR_VERSION:-}"' in installer
    assert "A pinned release is required" in installer
    assert "Invalid Yamlr release version" in installer
    assert 'gh attestation verify "${ARCHIVE_PATH}"' in installer
    assert '--repo "yamlr/yamlr"' in installer
    assert '--signer-workflow "yamlr/yamlr/.github/workflows/release-binaries.yml"' in installer
    assert '--signer-workflow "yamlr/yamlr/.github/workflows/release.yml"' not in installer
    assert '--source-ref "refs/tags/${VERSION}"' in installer
    assert "Refusing to install Yamlr" in installer

    release_path = REPO_ROOT / ".github" / "workflows" / "release.yml"
    release = yaml.safe_load(release_path.read_text(encoding="utf-8"))
    assert release["concurrency"]["group"] == "yamlr-release-${{ github.ref }}"
    publish = release["jobs"]["publish"]
    assert publish["permissions"]["id-token"] == "write"
    assert publish["permissions"]["attestations"] == "write"
    assert publish["permissions"]["artifact-metadata"] == "write"
    attestation = next(
        item for item in publish["steps"] if item.get("name") == "Attest release artifacts"
    )
    assert attestation["uses"] == "actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d"
    assert "release_assets/yamlr-*" in attestation["with"]["subject-path"]
    assert "website/public/install.sh" in attestation["with"]["subject-path"]
    assert "yamlr-native-windows-x86_64.zip" in release["jobs"]["build"]["steps"][3]["run"]
    assert "native-checksums.txt" in release["jobs"]["publish"]["steps"][2]["run"]
    assert "done > checksums.txt" not in release["jobs"]["publish"]["steps"][2]["run"]

    alternate_release = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "release-binaries.yml").read_text(encoding="utf-8")
    )
    assert alternate_release["concurrency"]["group"] == release["concurrency"]["group"]
    alternate_publish = alternate_release["jobs"]["publish-release"]
    assert alternate_publish["permissions"]["id-token"] == "write"
    assert alternate_publish["permissions"]["attestations"] == "write"
    assert alternate_publish["permissions"]["artifact-metadata"] == "write"
    assert any(
        item.get("uses") == attestation["uses"]
        for item in alternate_publish["steps"]
    )
    alternate_attestation = next(
        item for item in alternate_publish["steps"] if item.get("uses") == attestation["uses"]
    )
    assert "website/public/install.sh" in alternate_attestation["with"]["subject-path"]
    windows_packaging = next(
        item for item in alternate_release["jobs"]["build-release"]["steps"]
        if item.get("name") == "Package artifact (Windows)"
    )
    assert '"$hash  ${{ matrix.asset_name }}"' in windows_packaging["run"]

    assert "yamlr-windows-x86_64.zip" in alternate_release["jobs"]["build-release"]["strategy"]["matrix"]["include"][-1]["asset_name"]
    assert "yamlr-native-windows-x86_64.zip" in release["jobs"]["build"]["steps"][3]["run"]
    assert "checksums.txt" in next(
        item for item in alternate_publish["steps"] if item.get("name") == "Consolidate SHA-256 Checksums"
    )["run"]


def test_packaged_installers_do_not_resolve_a_moving_latest_release():
    shell_template = (REPO_ROOT / "scripts" / "internal" / "install.sh.in").read_text(encoding="utf-8")
    powershell_template = (REPO_ROOT / "scripts" / "internal" / "install.ps1.in").read_text(encoding="utf-8")
    shell_installer = (REPO_ROOT / "website" / "public" / "install.sh").read_text(encoding="utf-8")
    powershell_installer = (REPO_ROOT / "website" / "public" / "install.ps1").read_text(encoding="utf-8")

    for installer in (shell_template, powershell_template, shell_installer, powershell_installer):
        assert "releases/latest" not in installer
        assert "attestation verify" in installer
        assert "checksums.txt" in installer
        assert "release-binaries.yml" in installer

    bash_path_instruction = r'''echo 'export PATH=\"\$HOME/.yamlr/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc'''
    assert bash_path_instruction in shell_template
