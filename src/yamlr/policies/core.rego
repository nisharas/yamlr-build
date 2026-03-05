package yamlr.deny

# Helper: Aggregates all containers (init, standard, ephemeral)
all_containers[container] {
    some i
    doc := input[i]
    # Check for Deployment, StatefulSet, DaemonSet, Job, Pod
    # For simplicity, we look for pod templates (spec.template.spec) or pod specs (spec) directly?
    # Let's focus on Workloads with PodTemplates
    pod_spec := doc.spec.template.spec
    
    keys := ["containers", "initContainers", "ephemeralContainers"]
    some k in keys
    container := pod_spec[k][_]
}

# Helper: Direct Pods
all_containers[container] {
    some i
    doc := input[i]
    doc.kind == "Pod"
    container := doc.spec.containers[_]
}

# ------------------------------------------------------------------------------
# POLICY 1: Organization Standards (Labeling)
# ------------------------------------------------------------------------------

violation[{"msg": msg, "severity": "ERROR", "kind": kind, "name": name, "fix_id": "inject_label_cost_center", "fix": "Add 'cost-center' label", "rule_id": "yamlr/labels/cost-center"}] {
    some i
    doc := input[i]
    doc.kind == "Deployment"
    kind := doc.kind
    name := object.get(doc.metadata, "name", "unnamed")
    labels := object.get(doc.metadata, "labels", {})
    not labels["cost-center"]
    msg := sprintf("[Org Standard] Deployment '%v' is missing cost-center label", [name])
}

# ------------------------------------------------------------------------------
# POLICY 2: Security Best Practices
# ------------------------------------------------------------------------------

# Deny Privileged Containers
violation[{"msg": msg, "severity": "ERROR", "kind": "Workload", "name": name, "rule_id": "yamlr/security/privileged"}] {
    container := all_containers[_]
    container.securityContext.privileged == true
    name := container.name
    msg := sprintf("[Security] Container '%v' is running in privileged mode", [name])
}

# Deny Root User (Must runAsNonRoot)
violation[{"msg": msg, "severity": "WARNING", "kind": "Workload", "name": name, "fix": "Set securityContext.runAsNonRoot: true", "rule_id": "yamlr/security/run-as-non-root"}] {
    container := all_containers[_]
    # Check container level
    not container.securityContext.runAsNonRoot == true
    # Also check pod level? (Simplified for now)
    name := container.name
    msg := sprintf("[Security] Container '%v' should set runAsNonRoot: true", [name])
}

# ------------------------------------------------------------------------------
# POLICY 3: Operational Reliability
# ------------------------------------------------------------------------------

# Warn on 'latest' tag
violation[{"msg": msg, "severity": "WARNING", "kind": "Workload", "name": name, "rule_id": "yamlr/best-practice/no-latest"}] {
    container := all_containers[_]
    endswith(container.image, ":latest")
    name := container.name
    msg := sprintf("[Reliability] Container '%v' uses unstable 'latest' tag", [name])
}

# Warn on Missing Resource Limits
violation[{"msg": msg, "severity": "WARNING", "kind": "Workload", "name": name, "rule_id": "yamlr/best-practice/resource-limits"}] {
    container := all_containers[_]
    not container.resources.limits
    name := container.name
    msg := sprintf("[Reliability] Container '%v' relies on unbounded resources (missing limits)", [name])
}

# Warn on Missing Probes (Liveness/Readiness)
violation[{"msg": msg, "severity": "WARNING", "kind": "Workload", "name": name, "rule_id": "yamlr/best-practice/missing-probes"}] {
    container := all_containers[_]
    # Only for main containers (not init)?
    # We can't distinguish easily in helper, but good practice usually applies to long running containers
    not container.livenessProbe
    not container.readinessProbe
    name := container.name
    msg := sprintf("[Reliability] Container '%v' missing liveness/readiness probes", [name])
}
