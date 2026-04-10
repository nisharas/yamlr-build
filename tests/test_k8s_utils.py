import pytest

from yamlr.core.k8s_utils import extract_containers


def test_extract_containers_pod():
    doc = {"kind": "Pod", "spec": {"containers": [{"name": "c1"}], "initContainers": [{"name": "i1"}]}}
    containers = extract_containers(doc)
    assert len(containers) == 2
    assert {c["name"] for c in containers} == {"c1", "i1"}


def test_extract_containers_deployment():
    doc = {"kind": "Deployment", "spec": {"template": {"spec": {"containers": [{"name": "c2"}]}}}}
    containers = extract_containers(doc)
    assert len(containers) == 1
    assert containers[0]["name"] == "c2"


def test_extract_containers_cronjob():
    doc = {
        "kind": "CronJob",
        "spec": {"jobTemplate": {"spec": {"template": {"spec": {"containers": [{"name": "c3"}]}}}}},
    }
    containers = extract_containers(doc)
    assert len(containers) == 1
    assert containers[0]["name"] == "c3"


def test_extract_containers_empty():
    assert extract_containers({}) == []
    assert extract_containers({"kind": "Service"}) == []
    assert extract_containers({"kind": "Pod", "spec": {}}) == []


def test_extract_containers_invalid_spec():
    doc = {"kind": "Pod", "spec": "not-a-dict"}
    assert extract_containers(doc) == []
