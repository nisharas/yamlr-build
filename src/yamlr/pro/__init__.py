from __future__ import annotations
__all__ = ["AuthManager", "Exporter", "ProSurgeon", "ShieldEngine", "ClusterDetection"]

def __getattr__(name: str):
    if name == "AuthManager":
        from yamlr.pro.auth import AuthManager
        return AuthManager
    if name == "Exporter":
        from yamlr.pro.exporter import Exporter
        return Exporter
    if name == "ProSurgeon":
        from yamlr.pro.surgery import ProSurgeon
        return ProSurgeon
    if name == "ShieldEngine":
        from yamlr.pro.shield import ShieldEngine
        return ShieldEngine
    if name == "ClusterDetection":
        from yamlr.pro.cluster_detection import ClusterDetection
        return ClusterDetection
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
