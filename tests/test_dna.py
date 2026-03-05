import pytest
import re
import sys
from pathlib import Path
from yamlr.core.entrypoints.dna import handle_dna_command
from yamlr.core.engine import YamlrEngine

class MockConsole:
    def __init__(self):
        self.output = []
    def print(self, msg):
        self.output.append(msg)

@pytest.fixture
def engine():
    # Use a dummy catalog to avoid dependency issues in tests
    return YamlrEngine.quick(".")

hex_pattern = re.compile(r'[a-f0-9]{64}')

def get_dna_from_output(output):
    for line in output:
        match = hex_pattern.search(line)
        if match:
            return match.group()
    return None

def test_dna_stability(tmp_path, engine):
    """Verify that comments and whitespace don't change DNA."""
    file1 = tmp_path / "deployment1.yaml"
    file1.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx # This is a comment
spec:
  replicas: 3
    """)

    file2 = tmp_path / "deployment2.yaml"
    file2.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3 # Different comment location
    """)

    console1 = MockConsole()
    class Args:
        path = str(file1)
        expected_hash = None
        output = "text"
    
    res = handle_dna_command(Args(), engine, console1)
    dna1 = get_dna_from_output(console1.output)

    if dna1 is None:
        print("\nCONSOLE OUTPUT 1:", console1.output)
        pytest.fail(f"DNA 1 was None. Return code: {res}")

    console2 = MockConsole()
    Args.path = str(file2)
    handle_dna_command(Args(), engine, console2)
    dna2 = get_dna_from_output(console2.output)

    if dna2 is None:
        print("\nCONSOLE OUTPUT 2:", console2.output)
        pytest.fail("DNA 2 was None")

    assert dna1 == dna2
    assert dna1 is not None

def test_dna_change(tmp_path, engine):
    """Verify that changing a value changes DNA."""
    file1 = tmp_path / "deployment1.yaml"
    file1.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3
    """)

    file2 = tmp_path / "deployment2.yaml"
    file2.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 4
    """)

    console1 = MockConsole()
    class Args:
        path = str(file1)
        expected_hash = None
        output = "text"
    
    handle_dna_command(Args(), engine, console1)
    dna1 = get_dna_from_output(console1.output)

    if dna1 is None:
        print("\nCONSOLE OUTPUT:", console1.output)
        pytest.fail("DNA 1 was None")

    console2 = MockConsole()
    Args.path = str(file2)
    handle_dna_command(Args(), engine, console2)
    dna2 = get_dna_from_output(console2.output)

    if dna2 is None:
        print("\nCONSOLE OUTPUT:", console2.output)
        pytest.fail("DNA 2 was None")

    assert dna1 != dna2

def test_dna_verify(tmp_path, engine):
    """Verify DNA verification mode."""
    file1 = tmp_path / "deployment1.yaml"
    file1.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3
    """)

    console = MockConsole()
    class Args:
        path = str(file1)
        expected_hash = None
        output = "text"
    
    handle_dna_command(Args(), engine, console)
    dna = get_dna_from_output(console.output)

    if dna is None:
        print("\nCONSOLE OUTPUT:", console.output)
        pytest.fail("DNA was None")

    # Success
    Args.expected_hash = dna
    assert handle_dna_command(Args(), engine, console) == 0

    # Failure
    Args.expected_hash = "f" * 64
    assert handle_dna_command(Args(), engine, console) == 1
