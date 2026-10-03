import os

import pytest

from yamlr.knowledge.bible import BiblicalRegistry


def test_bible_registry_parse(temp_workspace):
    man_path = os.path.join(temp_workspace, "man1")
    os.makedirs(man_path)
    
    # Create dummy man page
    roff_content = r"""
.TH "YAMLR-TEST" "1" "May 2026" "Yamlr 0.1.0" "Yamlr Manual"
.SH "NAME"
yamlr-test \- Test command
.SH "DESCRIPTION"
This is a test command.
.PP
.SH "OPTIONS"
\fB--flag <ARG>\fR: A test flag
"""
    with open(os.path.join(man_path, "yamlr-test.1"), "w") as f:
        f.write(roff_content)
        
    registry = BiblicalRegistry(man_path=man_path)
    
    # Test lookup command
    res = registry.lookup("test")
    assert res is not None
    assert res["title"] == "Yamlr Test"
    assert "test command" in res["definition"]
    
    # Test lookup flag
    res_flag = registry.lookup("test", "--flag")
    assert res_flag is not None
    assert "A test flag" in res_flag["definition"]
    
    # Test missing command
    assert registry.lookup("missing") is None
    
    # Test missing flag
    assert registry.lookup("test", "--missing") is None

def test_bible_registry_no_dir(temp_workspace):
    registry = BiblicalRegistry(man_path=os.path.join(temp_workspace, "does_not_exist"))
    assert registry.lookup("test") is None
