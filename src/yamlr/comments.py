"""
Yamlr COMMENTS - The Intent Preserver
-------------------------------------
Hardened utilities for attaching comments to ruamel.yaml objects.
Deals with low-level CommentedMap/CommentedSeq structures.

Why: Standard ruamel.yaml APIs for comments are brittle and version-dependent. 
     This module provides a "Zero-Failure" interface for the Structurer.
"""

from __future__ import annotations
import logging
from ruamel.yaml.comments import CommentedMap, CommentedSeq

logger = logging.getLogger("yamlr.comments")

def yaml_set_start_comment(container, comment: str, indent: int = 0):
    """
    Safely attaches a multi-line comment above a YAML object (the container itself).
    """
    if not comment or not isinstance(comment, str):
        return

    # ruamel.yaml expectation: must end with a newline
    if not comment.endswith('\n'):
        comment += '\n'

    try:
        if hasattr(container, "_yaml_set_start_comment_hardened"):
             container._yaml_set_start_comment_hardened(comment, indent=indent)
        elif hasattr(container, "yaml_set_start_comment"):
             container.yaml_set_start_comment(comment, indent=indent)
    except Exception as e:
        logger.debug(f"Start-Comment injection failed: {e}")

def yaml_set_key_comment(container, key: str, comment: str, indent: int = 0):
    """
    Attaches a comment specifically ABOVE a key in a CommentedMap.
    Why: Resolves Finding 27.1 (Invisible Space Regression) for layout gaps between keys.
    """
    if not isinstance(container, CommentedMap) or not key or not comment:
        return

    if not comment.endswith('\n'):
        comment += '\n'

    try:
        # ruamel stores key-associated comments in ca.items[key][1] (leading)
        from ruamel.yaml.tokens import CommentToken
        from ruamel.yaml.error import CommentMark
        
        logger.debug("Setting key comment for '%s' on container with keys %s", key, list(container.keys()))
        # [GAPS FIX] We must use a list of tokens with valid Marks and column
        mark = CommentMark(indent)
        token = CommentToken(comment, mark, None, column=indent)
        
        # ca.items is a property that shouldn't be assigned directly, 
        # but indexing it works if the container is a CommentedMap.
        container.ca.items[key] = [None, [token], None, None]
    except Exception as e:
        logger.debug(f"Key-Comment injection failed for {key}: {e}")

def yaml_set_footer_comment(container, comment: str, indent: int = 0):
    """
    Attaches a comment at the END of a collection.
    Why: Preserves trailing gaps at the end of the file.
    """
    if not container or not comment:
        return
    
    if not comment.endswith('\n'):
        comment += '\n'
        
    try:
        from ruamel.yaml.tokens import CommentToken
        from ruamel.yaml.error import CommentMark
        
        mark = CommentMark(indent)
        token = CommentToken(comment, mark, None, column=indent)
        
        # ruamel footer comments for maps are in ca.comment[2]
        if not hasattr(container, 'ca') or container.ca is None:
            return
            
        if container.ca.comment is None:
            container.ca.comment = [None, None, None]
            
        # Ensure it has enough slots
        while len(container.ca.comment) < 3:
            container.ca.comment.append(None)
            
        container.ca.comment[2] = [token]
    except Exception as e:
        logger.debug(f"Footer-Comment injection failed: {e}")

def _hardened_method(self, comment: str, indent: int = 0):
    """The actual implementation injected into ruamel classes."""
    if not comment:
        return
    if not comment.endswith('\n'):
        comment += '\n'
    
    # Call the original method if it exists, but with our guard
    # We store the original during patching
    orig = getattr(self, "_yaml_orig_set_start_comment", None)
    if orig:
        try:
            orig(self, comment, indent=indent)
        except Exception:
            pass
    else:
        # If no original, we might be on a version that doesn't have it
        pass

# Monkey-patching to provide global availability
for cls in [CommentedMap, CommentedSeq]:
    if hasattr(cls, "yaml_set_start_comment") and not hasattr(cls, "_yaml_orig_set_start_comment"):
        setattr(cls, "_yaml_orig_set_start_comment", cls.yaml_set_start_comment)
        setattr(cls, "yaml_set_start_comment", _hardened_method)
    elif not hasattr(cls, "yaml_set_start_comment"):
        # If it doesn't have it at all, add our hardened one
        setattr(cls, "yaml_set_start_comment", _hardened_method)
    
    # Also add a specific namespaced one to avoid confusion
    setattr(cls, "_yaml_set_start_comment_hardened", _hardened_method)

__all__ = ["yaml_set_start_comment", "yaml_set_key_comment", "yaml_set_footer_comment"]
