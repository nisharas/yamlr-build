import pytest

import yamlr


def test_heal_yaml_public_api():
    yaml_in = "apiVersion: extensions/v1beta1\nkind: Deployment\nmetadata:\n  name: my-app # important comment\nspec:\n  replicas: 2\n"
    res = yamlr.heal_yaml(yaml_in)
    assert res.had_changes is True
    assert "# important comment" in res.healed_yaml
    assert len(res.changes) > 0
    assert repr(res).startswith("<HealResult")


def test_heal_yaml_forwards_kubernetes_version(monkeypatch):
    from types import SimpleNamespace

    calls = []

    def native_heal_yaml(content, k8s_version):
        calls.append((content, k8s_version))
        return content, []

    monkeypatch.setitem(
        __import__("sys").modules,
        "yamlr_native",
        SimpleNamespace(native_heal_yaml=native_heal_yaml),
    )

    yamlr.heal_yaml("kind: Ingress\n", k8s_version="1.22")

    assert calls == [("kind: Ingress\n", "1.22")]

def test_scan_yaml_public_api():
    yaml_in = "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-svc\nspec:\n  ports:\n  - port: 80\n"
    res = yamlr.scan_yaml(yaml_in)
    assert res["identity"] is not None
    assert res["identity"]["kind"] == "Service"
    assert res["identity"]["name"] == "my-svc"
