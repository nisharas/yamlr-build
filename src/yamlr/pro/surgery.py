#!/usr/bin/env python3
"""
Yamlr ENTERPRISE SURGERY
------------------------
Houses advanced, monetized epistemic and structural repair algorithms that 
were previously available in the OSS version.
"""

import logging
from typing import Any, List
from ruamel.yaml.comments import CommentedMap, CommentedSeq

logger = logging.getLogger("yamlr.pro.surgery")

T_MAP = CommentedMap
T_SEQ = CommentedSeq

class ProSurgeon:
    """Enterprise-only structural Yamlr operations."""
    
    @staticmethod
    def cast_to_array(val: Any, dot_path: str, key: str) -> List[Any]:
        """
        [Epistemic] Casts a Map or Scalar into a List of Objects.
        Handles the 'Key-as-Name' pattern (e.g., env: WEB: 1 -> env: [{name: WEB, value: 1}]).
        """
        if isinstance(val, list):
            return val
            
        if isinstance(val, (dict, T_MAP)):
            # If it's a map, and we expect a list of objects, check if we can flatten it
            # e.g., containers: web: {image: nginx} -> [{name: web, image: nginx}]
            flattened = []
            for k, v in val.items():
                if isinstance(v, (dict, T_MAP)):
                    # Key-as-Name: move internal key to 'name'
                    v_copy = T_MAP(v) if hasattr(v, "items") else dict(v)
                    v_copy["name"] = k
                    flattened.append(v_copy)
                else:
                    # Generic Key-Value: move to name/value
                    flattened.append({"name": k, "value": v})
            
            if flattened:
                logger.info(f"✨ Epistemic Repair: Cast Map -> List[Object] at {dot_path}.{key}")
                return T_SEQ(flattened)
        
        # Scalar -> List-of-one
        return T_SEQ([val])
