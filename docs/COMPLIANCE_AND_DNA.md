# Compliance & Semantic Manifest Verification

**Deterministic Integrity and Tamper-Evident Manifest State**

For regulated enterprise environments, verifying that manifests parse correctly is only half the battle. Teams must maintain tamper-evident proof that the code deployed to production matches the state that passed security policy checks. Yamlr provides semantic hashing and audit receipts for compliance tracking.

---

## 1. Semantic DNA Verification
Standard raw file hashes (SHA-256) are fragile: adding a comment or changing indentation breaks the hash even when the underlying workload definition is identical. Yamlr solves this by computing **Semantic DNA**.

### Hashing Methodology
1. **AST Extraction**: Parses the manifest into an Abstract Syntax Tree.
2. **Normalization**: Strips non-functional comments, whitespace variance, and quote style.
3. **Deterministic Canonicalization**: Canonicalizes map keys and lists into reproducible order.
4. **Cryptographic Hash**: Computes SHA-256 over the canonical semantic structure.

```bash
# Calculate the semantic fingerprint for a manifest
yamlr dna deployment.yaml
> [Semantic DNA] e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

# Verify a manifest against an approved baseline in CI
yamlr dna deployment.yaml --expected e3b0c442...
```

---

## 2. Audit Evidence Ledger
When Yamlr scans or heals manifests, it can generate an audit receipt recording the exact findings, applied mutations, and resulting semantic fingerprints.

### Evidence Bundling
Compliance teams can bundle these audit artifacts into verifiable archives for SOC2, ISO-27001, and CIS compliance audits:

```bash
# Bundle audit artifacts into an evidence archive
yamlr evidence ./manifests --output compliance-bundle.tar.gz
```

---

## 3. Policy Engine Reconciliation
Yamlr complements admission policy engines (Open Policy Agent, Kyverno) by acting as the auto-repair engine for their reported violations:

1. **Policy Ingestion**: Ingests policy violation reports (SARIF/JSON).
2. **AST Mapping**: Identifies the exact AST node and line number in the source manifest.
3. **Comment-Preserving Fix**: Applies the necessary correction while preserving surrounding formatting and comments.

```bash
# Scan and apply fixes for detected policy gaps
yamlr heal ./k8s --apply
```

---

> [!NOTE]
> **Audit Readiness**
> Semantic DNA hashing and timestamped evidence bundles establish an unbroken chain of custody for infrastructure manifests, ensuring reproducible verification across CI/CD and GitOps pipelines.
