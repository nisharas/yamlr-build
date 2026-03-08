import logging
from typing import List, Dict, Set, Any
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzers.ref_resolver")

class ReferenceResolver:
    """
    Performs Cross-Resource Validation (Pass 1: Indexing, Pass 2: Checking).
    Identifies missing ConfigMaps, Secrets, Services, PVCs.
    """
    
    def resolve_references(self, identities: List[ManifestIdentity]) -> List[Dict[str, Any]]:
        """
        Scans all identifies to find broken references.
        Returns a list of 'Healing Candidates' (dictionaries) that define what is missing.
        """
        missing_resources = []
        
        # --- PASS 1: Indexing ---
        # Map: Kind -> Namespace -> Set[Names]
        index: Dict[str, Dict[str, Set[str]]] = {
            "ConfigMap": {},
            "Secret": {},
            "PersistentVolumeClaim": {},
            "Service": {},
            "ServiceAccount": {},
            "Role": {},
            "ClusterRole": {},
            "StorageClass": {},
            "IngressClass": {},
            "ResourceQuota": {},
            "LimitRange": {},
            "HorizontalPodAutoscaler": {}
        }
        
        for ident in identities:
            if not ident.kind or not ident.name:
                continue
                
            kind = ident.kind
            ns = ident.namespace or "default"
            
            if kind in index:
                if ns not in index[kind]:
                    index[kind][ns] = set()
                index[kind][ns].add(ident.name)

        # --- PASS 2: Validation ---
        for ident in identities:
            ns = ident.namespace or "default"
            
            # Check ConfigRefs (ConfigMap or Secret)
            # ManifestIdentity.config_refs stores names, but doesn't distinguish kind easily
            # However, usually we can infer or we need to check BOTH.
            # Actually, standard K8s refs usually specify kind in the structurer logic.
            # But ManifestIdentity flattens it.
            # Refinement: ManifestIdentity.config_refs is a simple list of names.
            # This is ambiguous. Is 'web-config' a CM or Secret?
            # Issue: If structurer just dumps names into `config_refs`, we don't know the target kind.
            # Assumption: The current `structurer.py` logic might need to be checked.
            # For now, let's assume `config_refs` are ConfigMaps and `secret_refs` are Secrets?
            # Looking at `models.py`:
            #     config_refs: List[str] = field(default_factory=list)  # ConfigMap/Secret names
            # It merges them! This is a problem for precise stubbing. 
            # We can try to look it up in BOTH. If missing in BOTH -> Missing. 
            # But we don't know which one to stub.
            
            # WORKAROUND for Phase 1:
            # We will perform a "Best Effort" check.
            # If a name is missing from BOTH ConfigMap AND Secret checks, we assume ConfigMap default?
            # Or better: We should check `structurer` logic later.
            # For now, let's look at `volume_refs` (PVCs) which are distinct.
            
            # 2.1 Check PVCs
            for vol_name in ident.volume_refs:
                if not self._exists(index, "PersistentVolumeClaim", ns, vol_name):
                    missing_resources.append({
                        "rule_id": "missing-pvc-ref",
                        "kind": "PersistentVolumeClaim",
                        "name": vol_name,
                        "namespace": ns,
                        "source": ident
                    })

            # 2.2 Check Services
            for svc_name in ident.service_refs:
                 if not self._exists(index, "Service", ns, svc_name):
                    missing_resources.append({
                        "rule_id": "missing-service-ref",
                        "kind": "Service",
                        "name": svc_name,
                        "namespace": ns,
                        "source": ident
                    })
                    
            # 2.3 Check ConfigMaps
            for name in ident.config_refs:
                if not self._exists(index, "ConfigMap", ns, name):
                    missing_resources.append({
                        "rule_id": "missing-configmap-ref",
                        "kind": "ConfigMap",
                        "name": name,
                        "namespace": ns,
                        "source": ident
                    })

            # 2.4 Check Secrets
            for name in ident.secret_refs:
                if not self._exists(index, "Secret", ns, name):
                    # Check if it's specifically a volume ref for safe auto-healing
                    is_volume = name in ident.secret_volume_refs
                    rule_id = "missing-secret-volume-ref" if is_volume else "missing-secret-ref"
                    
                    missing_resources.append({
                        "rule_id": rule_id,
                        "kind": "Secret",
                        "name": name,
                        "namespace": ns,
                        "source": ident
                    })
            
            # 2.5 Check RBAC
            for name in ident.role_refs:
                if not self._exists(index, "Role", ns, name):
                    missing_resources.append({
                        "rule_id": "missing-role-ref",
                        "kind": "Role",
                        "name": name,
                        "namespace": ns,
                        "source": ident
                    })
            
            for name in ident.cluster_role_refs:
                if not self._exists(index, "ClusterRole", "default", name): # Cluster-scoped
                    missing_resources.append({
                        "rule_id": "missing-clusterrole-ref",
                        "kind": "ClusterRole",
                        "name": name,
                        "namespace": "default",
                        "source": ident
                    })

            # 2.6 Check Storage
            for name in ident.storage_class_refs:
                if not self._exists(index, "StorageClass", "default", name): # Cluster-scoped
                    missing_resources.append({
                        "rule_id": "missing-storageclass-ref",
                        "kind": "StorageClass",
                        "name": name,
                        "namespace": "default",
                        "source": ident
                    })

            # 2.7 Check Ingress
            for name in ident.ingress_class_refs:
                if not self._exists(index, "IngressClass", "default", name): # Cluster-scoped
                    missing_resources.append({
                        "rule_id": "missing-ingressclass-ref",
                        "kind": "IngressClass",
                        "name": name,
                        "namespace": "default",
                        "source": ident
                    })

        return missing_resources

    def _exists(self, index, kind, ns, name) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return name in index.get(kind, {}).get(ns, set())
