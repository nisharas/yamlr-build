# Security Architecture

**Local Manifest Processing & Data Privacy Framework**

Yamlr's scan and heal engine processes local manifests with bundled schemas. Standard local operation does not upload manifests. Optional integrations can make network requests when explicitly enabled or configured.

---

## 1. Local Manifest Processing and Optional Network Integrations
Unlike hosted configuration scanners, local scan and heal do not require uploading manifests or granting external repository access.

1. **Local Analysis**: The scan and heal engine parses and evaluates manifests on the workstation or CI runner.
2. **Bundled Schemas**: Kubernetes schemas used by local validation are bundled with the native distribution; this path does not fetch schemas at runtime.
3. **Local Credential Storage**: Active license tokens are stored in the operating system credential manager. Existing valid tokens in the legacy per-user config file are migrated there on first access and removed from the file after successful migration.
4. **Network Opt-Ins**: Scan telemetry requires `--push-telemetry`; Team entitlement renewal requires `YAMLR_LICENSE_AUTO_RENEW=true`. Renewal sends the signed entitlement token to the configured licensing gateway. Review these settings before running in an isolated environment.
5. **Other Integrations**: CI workflows may upload reports such as SARIF, and registry or hosted-service adapters may communicate with their configured endpoints. Disable those integrations for air-gapped operation.
6. **Telemetry Payload**: The scan-completion telemetry event contains the CLI version, event type, and timestamp; it does not include manifest contents, file paths, or repository URLs.

---

## 2. Multi-Stage Verification
To prevent erroneous automated changes, Yamlr validates every remediation across three layers:

| Layer | Responsibility |
|:---|:---|
| **Lexical & Syntax** | Verifies YAML syntax, indentation consistency, and comment preservation. |
| **Schema Validation** | Validates structure against official Kubernetes OpenAPI schemas for the target release. |
| **Relational Integrity** | Evaluates the ResourceGraph to ensure cross-resource references remain aligned. |

A file is only modified if all three layers certify the change as safe.

---

## 3. Security Hardening Auto-Repair
Yamlr can auto-remediate common security gaps to align with Pod Security Standards (PSS Restricted profile):

- **Identity Hardening**: Injects `runAsNonRoot: true` across container specs.
- **Filesystem Protection**: Sets `readOnlyRootFilesystem: true`.
- **Capability Dropping**: Drops unnecessary Linux capabilities (`drop: ["ALL"]`).
- **Network Isolation**: Identifies namespaces lacking default isolation and can generate matching NetworkPolicies.

---

## 4. Workspace Configuration & Boundary Controls
Platform teams can enforce global standards via the `.yamlr.yaml` workspace configuration:

- **Registry Enforcement**: Restricts container image registries to authorized internal domains.
- **Volume Restrictions**: Disallows dangerous volume types like unrestricted `hostPath`.
- **API Lifecycle**: Blocks manifests referencing deprecated or deleted API versions.

---

> [!NOTE]
> **Audit Trail**
> Every auto-repair session generates a timestamped receipt in `.yamlr/backups/`, enabling verification of what changed, when, and why.
