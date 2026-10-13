# The Healing Engine

**Yamlr Auto-Repair & Mutation Internals**

Yamlr couples static manifest analysis with an automated remediation engine. The Healing Engine is designed to apply multi-file fixes while strictly preserving formatting, comments, and semantic correctness.

---

## 1. Interactive & Preview Flow
By default, `yamlr heal` operates in preview mode to prevent unintended modifications:

1. **Side-by-Side Diffing**: Renders a color-coded terminal diff showing exact lines to be modified.
2. **Interactive Gating**: Prompts for confirmation before writing changes to disk:
   ```bash
   yamlr heal ./k8s/
   ```
3. **Atomic Commit**: When invoked with `--apply`, writes changes using an atomic write-and-rename pattern to prevent partially written files.

```bash
# Run in non-interactive CI mode
yamlr heal ./k8s --apply
```

---

## 2. Multi-Stage Safety Verification
Every mutation passes through three verification filters before being written to disk:

| Filter | Identifier | Scope |
|:---|:---|:---|
| **Structural Syntax** | `[SYN]` | Validates YAML syntax, indentation boundaries, and comment preservation. |
| **Schema Compliance** | `[SCH]` | Validates the mutated node against official Kubernetes OpenAPI v3 schemas. |
| **Relational Integrity**| `[REL]` | Re-evaluates the ResourceGraph to verify that selectors, ports, and refs remain aligned. |

**If an automated repair violates any safety filter, the mutation is aborted and the file is left unchanged.**

---

## 3. Structural Type Remediation
A frequent source of Kubernetes admission errors is YAML type mismatch (e.g. declaring a map where Kubernetes expects an array of maps). Yamlr includes transformation logic for:

- **Type Alignment**: Converts malformed maps to valid arrays of maps without dropping nested child keys.
- **Port Alignment**: Harmonizes Service `targetPort` definitions with container `containerPort` values.
- **HPA / Replica De-confliction**: Removes hardcoded `replicas` from Deployments when a HorizontalPodAutoscaler is actively managing the workload.
- **Memory Unit & Millibyte Sanitizer (`RES-004`)**: Sanitizes fatal millibytes (`500m` -> `500Mi`) and non-standard suffixes (`500mb`, `1gb`) that cause instantaneous container OOMKilled crashes. Preserves legitimate decimal SI notation (`200M`, `500G`).
- **Quoted Integer Normalizer (`TYP-002`)**: Normalizes template-rendered quoted integers on strict OpenAPI integer fields (`containerPort: "8080"`, `replicas: "3"`).
- **Probe Startup CrashLoop Guard (`REL-014`)**: Injects protective `initialDelaySeconds` when startup probes are omitted, guarding slow-booting workloads from premature health-check kill loops.
- **Image Tag Pull Policy Alignment (`IMG-002`)**: Enforces `imagePullPolicy: Always` on floating/latest tags and preserves immutable digest pull behavior.
- **Dangling Null-Sequence Pruner (`SYN-008`)**: Prunes orphaned sequence keys (`env:`, `args:`) whose items were commented out, preventing schema null validation rejections.
- **ConfigMap Credential Leakage Doctor (`SEC-016`)**: Flags and quarantines high-risk plaintext secrets accidentally committed into unencrypted ConfigMaps.
- **Zero-Downtime Rollout PreStop Drain Healer (`REL-015`, `REL-017`)**: Injects protective `preStop: sleep 5` hooks on web containers to eliminate HTTP 502/504 errors caused by kube-proxy/ingress endpoint propagation delays during rollouts. Audits shared probe paths to prevent cascading restart storms.
- **CoreDNS ExternalName FQDN & HostPort Healer (`NET-009`, `NET-010`)**: Appends trailing dots to `ExternalName` FQDNs to prevent search-path DNS query amplification loops, and synthesizes `podAntiAffinity` on multi-replica workloads with `hostPort` to prevent node port scheduling collisions.
- **CIS Benchmark 5.1.5 Token Guard & ReadOnly RootFS Healer (`SEC-017`, `SEC-018`, `SEC-019`)**: Enforces `automountServiceAccountToken: false` to stop SSRF token scraping, synthesizes companion in-memory `emptyDir` volumes at `/tmp` for `readOnlyRootFilesystem: true`, and alerts on dangerous host Docker socket mounts.
- **Operational Invariants, CronJobs & Scientific Floats (`OPS-004`, `OPS-005`, `TYP-003`, `SYN-009`)**: Stamps explicit `timeZone: "Etc/UTC"` on CronJobs to stop DST drift, enforces `concurrencyPolicy: Forbid` against batch job overlap storms, converts scientific float CPU quantities (`0.001` -> `"1m"`), and normalizes singleton maps under `ports:` or `env:` into valid YAML sequences.
- **POSIX Octal Permission Normalizer (`STO-008` / Trap 39)**: Mathematically converts POSIX octal file permissions in `volumes[*].configMap` or `secret` `defaultMode` (e.g. `"0755"`, `0755`, `"644"`, `"0644"`) into canonical base-10 integer scalars (`493`, `420`) required by the Kubernetes OpenAPI schema.
- **Unary Affinity Operator Redundancy Pruner (`SEL-002` / Trap 40)**: Prunes redundant `values:` arrays from `matchExpressions` when the operator is unary (`Exists` or `DoesNotExist`), satisfying strict `kube-apiserver` operator exclusivity.
- **Strict OpenAPI Boolean Unquoter (`SCHEMA-003` / Trap 41)**: Unquotes stringified booleans (`"true"` / `"false"`) on strict OpenAPI boolean fields (`readOnlyRootFilesystem`, `runAsNonRoot`, `privileged`, etc.).
- **Headless Service `clusterIP: None` Canonicalizer (`NET-012` / Trap 42)**: Normalizes case-insensitive or quoted variations of `clusterIP: "none"` or `none` to the canonical unquoted `None` required for stateful headless direct-pod DNS resolution.
- **GitOps Live Cluster Export Sanitizer (`GTO-003` / Trap 43)**: Purges server-only runtime artifacts (`status:`, `metadata.creationTimestamp: null`, `resourceVersion:`, `uid:`, `managedFields:`) from manifests dumped via `kubectl get -o yaml`, preventing GitOps diff-flap and `409 Conflict` admission failures.
- **Downward API `fieldPath` Syntax Healer (`DAPI-001` / Trap 44)**: Normalizes malformed Downward API label/annotation references (`metadata.labels.app` or `metadata.labels["app"]`) into the canonical Kubernetes subscript syntax (`metadata.labels['app']`), preventing kubelet container startup rejections.
- **PriorityClass `preemptionPolicy` Case Normalizer (Trap 45)**: Normalizes case-insensitive `preemptionPolicy` declarations (`"never"` -> `Never`, `"preemptlowerpriority"` -> `PreemptLowerPriority`) to satisfy strict admission schema validation.
- **VolumeMount `mountPropagation` Enum Normalizer (Trap 46)**: Normalizes case-insensitive mount propagation values (`"bidirectional"` -> `Bidirectional`, `"hosttocontainer"` -> `HostToContainer`, `"none"` -> `None`).
- **Secret Volume Key Canonicalizer (`SEC-021` / Trap 47)**: Normalizes `name:` collisions under `spec.volumes[*].secret` to the canonical `secretName:` property required by the Kubernetes SecretVolumeSource schema.
- **Metadata Annotation Boolean Contract Normalizer (`ANN-001` / Trap 48)**: Normalizes boolean annotations (e.g. `cluster-autoscaler.kubernetes.io/safe-to-evict`, `karpenter.sh/do-not-disrupt`) from raw YAML boolean scalars (`true`/`false`) or capitalized strings (`"True"`) into canonical quoted lowercase strings (`"true"` / `"false"`), satisfying string map admission schema requirements.
- **Service Session Affinity Timeout Guard (`NET-013` / Trap 49)**: Unquotes integer scalars and clamps `sessionAffinityConfig.clientIP.timeoutSeconds` into the valid Kubernetes admission range ($1 \le \text{timeoutSeconds} \le 86400$).
- **Pod SecurityContext `fsGroupChangePolicy` Normalizer (Trap 50)**: Normalizes case-insensitive values (`"onrootmismatch"` -> `OnRootMismatch`, `"always"` -> `Always`) to comply with Kubernetes OpenAPI v3 definitions.
- **NodeSelector Sequence List Flattener (`TYP-004` / Trap 51)**: Automatically converts invalid sequence lists under `spec.nodeSelector` (`- zone: us-east-1a`) into a valid string mapping (`zone: us-east-1a`), satisfying the `map[string]string` schema contract.
- **Ingress Class Annotation Promotion (`ING-002` / Trap 52)**: Promotes legacy `kubernetes.io/ingress.class` annotations on Kubernetes 1.22+ Ingresses to the first-class `spec.ingressClassName` field and prunes the deprecated annotation.
- **Service NodePort Alignment & Low-Port Pruner (`NET-014` / Trap 53)**: Unquotes stringified `nodePort` values to integers and strips invalid low nodePorts ($< 30000$ or $> 32767$), allowing the cluster to safely auto-assign an available port within the standard range.
- **Topology Key Deprecation Modernizer (`TOPO-001` / Trap 54)**: Modernizes obsolete beta failure-domain and topology keys (`failure-domain.beta.kubernetes.io/*`, `beta.kubernetes.io/*`) across `nodeSelector`, `topologySpreadConstraints.topologyKey`, and `matchExpressions.key` to their GA replacements (`topology.kubernetes.io/*`, `kubernetes.io/*`).
- **Service SessionAffinity & Config Harmonizer (`NET-015` / Trap 55)**: Enforces mutual dependency between `sessionAffinity` and `sessionAffinityConfig`, promoting `sessionAffinity: ClientIP` when `clientIP` settings are configured and pruning orphaned config when `None`.
- **Job & CronJob RestartPolicy Harmonizer (`JOB-001` / Trap 56)**: Replaces forbidden `restartPolicy: Always` on Job and CronJob pod templates with canonical `restartPolicy: OnFailure`, fulfilling the batch run-to-completion contract.
- **ImagePullSecrets Shape Normalizer (`SEC-022` / Trap 57)**: Normalizes raw scalar string values and string sequences under `imagePullSecrets` into valid `LocalObjectReference` sequence items (`- name: <secret-name>`).
- **Ingress Relative Path Prefix Guard (`ING-003` / Trap 58)**: Automatically prepends a leading slash `/` to relative URI paths under `spec.rules[*].http.paths[*].path`, satisfying Kubernetes Ingress RFC specifications.
- **Ingress Wildcard Host Alias Quote Guard (`SYN-014` / Trap 59)**: Automatically quotes unquoted wildcard host patterns (`host: *` or `host: *.domain.com` -> `host: "*"`), preventing YAML parsers from failing on illegal alias indicators.
- **Memory Unit & Quantity Suffix Normalizer (`RES-006` / Trap 60)**: Normalizes case variations in binary SI resource quantities (`500mi` / `500MI` -> `500Mi`, `1gi` / `1GI` -> `1Gi`, `Ki`, `Ti`, `Pi`) to satisfy official Kubernetes Quantity syntax.
- **HostPath Volume Explicit Type Guard (`SEC-023` / Trap 61)**: Injects explicit `type: DirectoryOrCreate` or `FileOrCreate` into `spec.volumes[*].hostPath` when omitted, preventing unvalidated path escapes and satisfying CIS benchmark controls.
- **Service PublishNotReadyAddresses Contract Normalizer (`NET-016` / Trap 62)**: Unquotes stringified boolean values (`"true"` / `"false"`) on `spec.publishNotReadyAddresses` and promotes legacy `service.alpha.kubernetes.io/tolerate-unready-endpoints` annotations to the canonical spec field.
- **Job TTL Duration Unquoter & Range Clamper (`JOB-002` / Trap 63)**: Unquotes stringified numbers on `spec.ttlSecondsAfterFinished` to integer scalars and safely clamps negative values to `0`.
- **Job CompletionMode Enum Normalizer (`JOB-003` / Trap 64)**: Normalizes case-insensitive `completionMode` values (`"indexed"`, `"nonindexed"`) to canonical Kubernetes batch enum values (`Indexed`, `NonIndexed`).
- **EmptyDir Storage Medium Canonicalizer (`VOL-001` / Trap 65)**: Normalizes case-insensitive `spec.volumes[*].emptyDir.medium` values (`"memory"`, `"ram"`) to canonical `Memory` required by the kubelet.
- **Probe Timeout Deadlock Safeguard (`PRB-006` / Trap 66)**: Resolves container probe scheduling deadlocks where `timeoutSeconds >= periodSeconds` by clamping `periodSeconds = timeoutSeconds + 1`.
- **HPA Replica Bound Inversion Healer (`AUT-002` / Trap 67)**: Resolves invalid inverted bounds where `minReplicas > maxReplicas` by aligning `maxReplicas = minReplicas` to maintain the $max \ge min$ invariant.
- **Ingress Backend Port Mutual Exclusivity Resolver (`ING-004` / Trap 68)**: Resolves OpenAPI `oneOf` union conflicts under Ingress `backend.service.port` when both `number` and `name` are declared by retaining numeric `number` and pruning redundant `name`.
- **Unindented Multiline Block Scalar Healer (`SYN-015` / Trap 69)**: Detects and repairs block scalar bodies (`|`, `|-`, `|+`, `>`, `>-`, `>+`, `|2`) whose text lines were accidentally pasted at or shallower than the parent dictionary key's indentation level (e.g. `lua_scripts: |\nfunction envoy_on_response...` at indent 4 instead of 6). Re-aligns scalar body lines to `key_indent + 2` while preserving all inner relative indentation, blank lines, and comments, without mutating peer keys or subsequent mappings.
- **UTF-16 BOM Transcoder (`ENC-001` / Trap 70)**: Detects UTF-16 LE and BE byte order marks from Windows/legacy PowerShell exported manifests and cleanly transcodes input text to canonical UTF-8 prior to YAML parsing.
- **Orphaned Block Indentation Healer (`SYN-016` / Trap 71)**: Identifies blocks left indented when an author comments out their parent mapping header (e.g., `# spec:`), safely shifting orphaned child keys leftward to restore syntactic validity.
- **Sequence List Bullet Indentation Healer (`SYN-017` / Trap 72)**: Re-aligns over-indented list bullets (`-`) to match their parent sequence scope, preventing parser errors without altering map structure.
- **Standalone Anchor Colon Healer (`SYN-018` / Trap 73)**: Corrects malformed standalone anchor declarations containing extraneous colons (`context:\n  &context:` followed by `<<: *context`) into clean anchor maps (`context: &context`), enabling YAML merge key resolution.
- **Glued Colon Spacing Healer (`SYN-019` / Trap 74)**: Identifies and repairs glued unspaced colons on resource quantities and scalar values (`memory:256Mi`, `cpu:150m` -> `memory: 256Mi`, `cpu: 150m`), preventing simple key scanner crashes while safeguarding URLs (`http://`) and existing whitespace.
- **Unicode Comment Quotation Preserver (`ENC-002` / Trap 75)**: Ensures smart and typographic quotes (`’`, `‘`, `“`, `”`) within human code comments are preserved byte-for-byte during lexing and sharding passes, guaranteeing 100% Gate 1 zero-loss comment retention across internationalized manifests.
- **Helm Values Secret Annotation Comment Appender (`VAL-001` / Trap 76)**: Appends automated diagnostic and security tags (`# yamlr [SEC-003]`) to lines in Helm `values.yaml` files alongside existing author comments rather than overwriting them, upholding Gate 1 comment preservation invariants across chart values hierarchies.
- **Empty Flow Mapping Pre-Parse Stripper (`SYN-019` / Trap 77)**: Detects empty inline flow collections (`selector: {}` or `annotations: {}`) followed immediately by indented block mappings on un-commented lines, safely stripping conflicting inline `{}` or `[]` tokens so the mapping parses cleanly as canonical YAML 1.2 block mapping.
- **AST Lift Ordering Invariant Stabilizer (`STRUCT-001` / Trap 78)**: Enforces stable, top-to-bottom document index order when lifting nested or misplaced child elements into parent mappings, guaranteeing strict mathematical idempotency ($h(h(x)) == h(x)$) without diff drift.
- **Container Environment Variable String Schema Guard (`ENV-001` / Trap 79)**: Ensures boolean scalar values specified under container `env[].value` (e.g. `value: true`) conform to Kubernetes OpenAPI v3 string schema contracts without triggering false-positive type mismatch failures.

---

## 4. Multi-Layered Recovery (The Vault)
Remediation is always non-destructive and fully reversible:

- **Session Rollback**: `yamlr rollback` reverts the most recent healing session across all affected files.
- **Single-File Restore**: `yamlr restore <path>` restores an individual manifest from the backup vault.
- **Audit Journal**: Every mutation writes a timestamped record to `.yamlr/backups/`, enabling full audit traceability.

---

> [!NOTE]
> **Deterministic Remediation**
> The Healing Engine is strictly deterministic. Identical input files with identical configuration will produce byte-for-byte identical output on every run.
