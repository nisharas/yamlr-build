"""Guard the mixed Python/Rust distribution shape before clean installation."""

import importlib.util
from pathlib import Path
import zipfile

import pytest

spec = importlib.util.spec_from_file_location(
    "wheel_smoke", Path(__file__).resolve().parents[1] / "scripts/ci/smoke_wheel.py"
)
wheel_smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wheel_smoke)

REQUIRED = [
    "yamlr/__init__.py",
    "yamlr/__main__.py",
    "yamlr/_find_bin.py",
    "yamlr_native/__init__.py",
]


def wheel(tmp_path, names):
    path = tmp_path / "candidate.whl"
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, b"")
    return path


@pytest.mark.parametrize(
    "extension", ["yamlr_native/yamlr_native.pyd", "yamlr_native/yamlr_native.abi3.so"]
)
def test_supported_platform_layout(tmp_path, extension):
    wheel_smoke.verify_wheel_layout(wheel(tmp_path, [*REQUIRED, extension]))


@pytest.mark.parametrize(
    "names",
    [
        ["yamlr_native.pyd"],
        REQUIRED,
        [*REQUIRED, "yamlr_native/yamlr_native.pyd", "yamlr/_archive/cli/main.py"],
        [*REQUIRED, "yamlr_native/yamlr_native.pyd", "yamlr/pro/old.py"],
    ],
)
def test_rejects_incomplete_or_archived_layout(tmp_path, names):
    with pytest.raises(ValueError):
        wheel_smoke.verify_wheel_layout(wheel(tmp_path, names))
