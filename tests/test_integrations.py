import os
import shutil

import pytest

from yamlr.integrations import cmd_install_action, cmd_install_hook


def test_install_hook_no_git(temp_workspace):
    """Verify failure if .git is missing."""
    with patch('os.getcwd', return_value=temp_workspace):
        result = cmd_install_hook()
        assert result is False

def test_install_hook_success(temp_workspace):
    """Verify successful hook installation."""
    git_dir = os.path.join(temp_workspace, ".git")
    os.makedirs(git_dir)
    
    with patch('os.getcwd', return_value=temp_workspace):
        result = cmd_install_hook()
        assert result is True
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
        assert os.path.exists(hook_path)
        with open(hook_path, 'r') as f:
            content = f.read()
            assert "yamlr scan" in content

def test_install_action(temp_workspace):
    """Verify GitHub Action generation."""
    with patch('os.getcwd', return_value=temp_workspace):
        result = cmd_install_action()
        assert result is True
        action_path = os.path.join(temp_workspace, ".github", "workflows", "yamlr-safety.yml")
        assert os.path.exists(action_path)
        with open(action_path, 'r') as f:
            content = f.read()
            assert "yamlr/action@v1" in content

from unittest.mock import patch
