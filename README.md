# 🛡 yamlr — Kubernetes manifest safety & healing engine
![Version](https://img.shields.io/badge/version-0.1.0-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Kubernetes-lightgrey?style=flat-square)
![CI/CD Ready](https://img.shields.io/badge/CI%2FCD-ready-success?style=flat-square)

**Kubernetes validates syntax. Yamlr validates system integrity.**

`kubectl apply` can succeed — and your cluster can still break.

Yamlr analyzes how your Kubernetes resources interact *before* deployment, catching logical misconfigurations that YAML validation and schema checks miss.

---

## 🚨 What Yamlr Catches

Yamlr builds a dependency graph across your manifests to detect silent semantic failures:

- **Ghost Services** — Services pointing to non-existent Pods  
- **Port Mismatches** — Container ports misaligned with Service targets  
- **Broken References** — Missing ConfigMaps, Secrets, PVCs  
- **Selector Drift** — Deployment labels no longer match Services  
- **Deprecated APIs** — Removed or unsafe Kubernetes versions  

> 🧩 **Yamlr thinks in relationships — not individual files.**
---

## ⚡ Try It in 60 Seconds

```bash
# Install (macOS / Linux)
curl -fsSL https://yamlr.dev/install.sh | bash

# Scan your manifests
yamlr scan .
````

You’ll instantly see:

* Risk level
* Impact scope
* Clear explanation
* Suggested safe remediation

---

## 🔍 Discover What's Protected

Yamlr isn't a black box. You can explore the full breadth of our safety engine natively:

```bash
# View all 26+ typed safety relationships
yamlr rules

# Deep dive into a specific protection
yamlr explain k8s/service-selector-mismatch
```

From **Ghost Services** to **Network Isolation Risks**, Yamlr gives you total visibility into your infrastructure's health.

---

## 🧠 Why Not Just kubectl?

`kubectl` checks structure.

Yamlr checks whether your system will behave correctly once deployed.

Example:

```yaml
# Service selects app=api
selector:
  app: api
```

```yaml
# Deployment labels app=backend
labels:
  app: backend
```

* Kubernetes accepts both.
* Traffic never routes.
> **Yamlr catches this mismatch instantly — before downtime hits.**

---

## 🔮 Safe Kubernetes Upgrades

Upgrade deprecated APIs safely:

```bash
yamlr upgrade ./manifests --to 1.31
```

Yamlr identifies:

* Removed APIs
* Field behavior changes
* Version incompatibilities

Before your cluster upgrade fails.

---

## 🩹 Deterministic Auto-Healing

Yamlr doesn’t just report risk — it can fix it safely.

```bash
# Interactive repair
yamlr heal manifests/

# Preview changes safely
yamlr heal manifests/ --dry-run
```

Yamlr explains:

* What will change
* Why it’s safe
* What dependencies are affected

> **Free users can experience limited automated repairs.**
> **Pro unlocks unlimited batch remediation and CI automation.**

---

## 🔁 CI/CD Integration

Add Yamlr as a pre-flight safety check in CI:

```bash
# Fast syntax validation
yamlr check .

# Deep semantic scan (SARIF output supported)
yamlr scan . --output sarif
```

Yamlr can:

* Comment risk summaries on pull requests
* Gate merges by risk threshold
* Stream results for large mono-repos

> Guard and Surgeon are also available as **GitHub Actions** for easy CI integration.

---

## 🧩 Guard (Free) vs 🩺 Surgeon (Pro)

### 🧩 Yamlr Guard — Free (GitHub Action + CLI)

* Unlimited scanning
* Risk diagnostics
* Version awareness
* Health scoring

### 🩺 Yamlr Surgeon — Pro (GitHub Action + CLI)

* Automated cross-resource remediation
* Batch fixing across repositories
* CI auto-PR fixes
* Compliance export artifacts

Detection is free.
Safe automation scales with your team.

---

## 🧰 Core Commands

```bash
yamlr scan .          # Full safety analysis
yamlr heal .          # Apply safe remediation
yamlr status          # Repository safety score
yamlr rules           # View active safety rules
yamlr stats           # Surgical ROI & savings dashboard
catalog update  # Update Kubernetes schema catalog
```

---

## 🌐 Ecosystem Integrations

* GitHub Actions
* GitLab CI
* VS Code Extension (real-time semantic diagnostics)

---

## 📦 Installation

Download the latest native executable for:

* macOS
* Linux
* Windows

Package managers (coming soon):

```bash
brew install yamlr/tap/yamlr
choco install yamlr
```

---

## 🏢 Yamlr Pro (Enterprise)

Yamlr Pro unlocks scalable remediation and automation for teams operating production Kubernetes environments.

Upgrade anytime:

```bash
yamlr auth login
```
---

## 🤝 Contributing
See [CONTRIBUTING.md](docs/CONTRIBUTING.md) to get started building new Analyzers and Healers.

## 📄 License
Yamlr is a commercial product.
- **Core Engine & Extensions:** are Proprietary. All rights reserved.

---
---
**🛠 yamlr — Kubernetes manifest safety & healing engine**

Learn more: https://yamlr.dev

