"""Tests for hermetic offline execution and embedded schema rodata."""
import socket
from unittest.mock import patch

import pytest
import yamlr_native

TEST_DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: hermetic-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hermetic
  template:
    metadata:
      labels:
        app: hermetic
    spec:
      containers:
        - name: app
          image: nginx:1.24
"""


def test_schema_rodata_embedded_versions():
    """Verify standard Kubernetes schemas v1.21 through v1.37 are embedded in binary rodata."""
    for minor in range(21, 38):
        version_str = f"1.{minor}"
        schemas = yamlr_native.native_get_schema_for_version(version_str)
        assert len(schemas) > 0, f"Schema bundle missing for K8s v{version_str}"
        kinds = [s.kind for s in schemas]
        assert "Deployment" in kinds
        assert "Service" in kinds


def test_hermetic_execution_zero_network_egress():
    """Verify manifest formatting and healing executes with zero socket connections."""
    def guarded_socket(*args, **kwargs):
        raise RuntimeError("Network egress attempted during hermetic execution!")

    with patch.object(socket, 'socket', side_effect=guarded_socket):
        # Sharding & Structuring
        shards = yamlr_native.native_shard(TEST_DEPLOYMENT)
        assert len(shards) > 0

        manifest = yamlr_native.native_structurize(shards)
        assert manifest is not None

        # Formatting
        formatted = yamlr_native.native_format_yaml(TEST_DEPLOYMENT)
        assert "apiVersion: apps/v1" in formatted

        # Healing
        from yamlr import heal_yaml
        res = heal_yaml(TEST_DEPLOYMENT)
        assert res is not None
