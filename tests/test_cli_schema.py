"""Tests for yamlr schema CLI subcommand."""
import os
import tempfile
from unittest.mock import MagicMock

from yamlr.cli.schema_handler import cmd_schema


def test_cli_schema_lifecycle():
    """Test schema ingest, list, and clean via cmd_schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "my_crd.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")

        with open(crd_file, "w", encoding="utf-8") as f:
            f.write("""apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: myresources.example.com
spec:
  group: example.com
  names:
    kind: MyResource
  versions:
    - name: v1
      schema:
        openAPIV3Schema:
          type: object
          properties:
            replicas:
              type: integer
""")

        # 1. Ingest
        args_ingest = MagicMock()
        args_ingest.schema_action = "ingest"
        args_ingest.path = crd_file
        args_ingest.out = schema_dir
        cmd_schema(args_ingest)

        assert os.path.exists(os.path.join(schema_dir, "myresource_v1.json"))

        # 2. List
        args_list = MagicMock()
        args_list.schema_action = "list"
        args_list.dir = schema_dir
        cmd_schema(args_list)

        # 3. Clean
        args_clean = MagicMock()
        args_clean.schema_action = "clean"
        args_clean.dir = schema_dir
        cmd_schema(args_clean)

        assert not os.path.exists(os.path.join(schema_dir, "myresource_v1.json"))
