# Yamlr vs Monokle: Competitive Analysis

**Purpose:** Detailed comparison between Yamlr and Monokle for strategic positioning.  
**Last Updated:** 2026-02-15

---

## Executive Summary

| Aspect | Yamlr | Monokle |
|:--|:--|:--|
| **Primary Function** | YAML healing + validation | YAML validation + IDE |
| **Core Differentiator** | Auto-fix (healing) | Visual editing + cluster inspection |
| **Architecture** | CLI-first, engine library | Desktop IDE + CLI + VS Code |
| **Business Model** | Private, freemium SaaS | Open-source (Cloud EOL April 2024) |
| **Status** | Active development | Desktop OSS only (Cloud discontinued) |

**Key Insight:** Monokle Cloud's EOL creates opportunity. Monokle Desktop remains OSS but lacks commercial backing. Yamlr can capture teams who need enterprise support + healing.

---

## Feature Comparison Matrix

### Core Capabilities

| Feature | Yamlr | Monokle | Notes |
|:--|:--:|:--:|:--|
| **YAML Validation** | ✅ | ✅ | Both validate against K8s schemas |
| **Auto-Healing** | ✅ | ❌ | **Yamlr's key differentiator** |
| **Cross-Resource Analysis** | ✅ | ✅ | Both detect broken refs |
| **OPA/Rego Policy Support** | ✅ | ✅ | Both integrate with OPA |
| **Helm Chart Support** | 🚧 Roadmap | ✅ | Monokle has native Helm preview |
| **Kustomize Support** | 🚧 Roadmap | ✅ | Monokle has overlay preview |
| **CLI Tool** | ✅ | ✅ | Both have CLIs |
| **VS Code Extension** | ✅ | ✅ | Both have extensions with real-time diagnostics |
| **Desktop IDE** | ❌ | ✅ | Monokle-only feature |
| **Cluster Inspection** | 🚧 Roadmap | ✅ | Monokle connects to live clusters |
| **Git Integration** | 🚧 Roadmap | ✅ | Monokle has branch compare |
| **SARIF Output** | ✅ | ✅ | Both support GitHub CodeScan |

### Validation & Policy

| Feature | Yamlr | Monokle | Notes |
|:--|:--:|:--:|:--|
| **Schema Validation** | ✅ | ✅ | K8s OpenAPI schemas |
| **Best Practices** | ✅ | ✅ | Resource limits, probes, etc. |
| **Security Policies** | ✅ | ✅ | Pod Security Standards |
| **Deprecation Detection** | ✅ | ✅ | API version migrations |
| **Custom Validators** | 🚧 Plugin API | ✅ TypeScript | Monokle is more mature |
| **CRD Support** | ✅ | ✅ | Both support custom schemas |

### Developer Experience

| Feature | Yamlr | Monokle | Notes |
|:--|:--:|:--:|:--|
| **Error → Fix Mapping** | ✅ | ❌ | Yamlr shows exact fix command |
| **Typo Suggestions** | ✅ | ❌ | Yamlr suggests "did you mean?" |
| **Interactive Healing** | ✅ | ❌ | Yamlr has diff preview + confirm |
| **Visual YAML Editor** | ❌ | ✅ | Monokle has form-based editing |
| **Resource Graph Visualization** | ❌ | ✅ | Monokle shows visual relationships |
| **Template Generation** | ❌ | ✅ | Monokle creates resources from templates |

### CI/CD & GitOps

| Feature | Yamlr | Monokle | Notes |
|:--|:--:|:--:|:--|
| **GitHub Actions** | ✅ | ✅ | Both have actions (Yamlr: scan + heal) |
| **GitHub Bot** | ✅ | ✅ | Yamlr Surgeon auto-commits repairs |
| **GitLab CI** | 🚧 Roadmap | ❌ | Neither has yet |
| **Argo CD Integration** | 🚧 Roadmap | ❌ | Neither has yet |
| **Pre-commit Hook** | ✅ | ✅ | Both support |

### Enterprise Features

| Feature | Yamlr | Monokle | Notes |
|:--|:--:|:--:|:--|
| **SSO/SAML** | 🚧 Roadmap | ❌ (Cloud EOL) | Yamlr planning |
| **Telemetry Dashboard** | 🚧 Roadmap | ❌ (Cloud EOL) | Yamlr planning |
| **Team Policy Management** | 🚧 Roadmap | ❌ (Cloud EOL) | **Opportunity** |
| **SOC2/Compliance** | 🚧 Roadmap | ❌ | Neither has yet |
| **Commercial Support** | ✅ Planned | ❌ (Cloud EOL) | **Major Yamlr advantage** |

---

## Architecture Comparison

### Yamlr Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLI / Engine API                    │
├─────────────────────────────────────────────────────────┤
│  Parsers        │  Analyzers       │  Healers           │
│  ├─ lexer.py    │  ├─ schema.py    │  ├─ indentation    │
│  ├─ scanner.py  │  ├─ best_prac    │  ├─ quotes         │
│  ├─ structurer  │  ├─ cross_res    │  ├─ colons         │
│  └─ pipeline    │  └─ opa_adapter  │  └─ migration      │
├─────────────────────────────────────────────────────────┤
│              Core Engine (engine.py, 48KB)              │
│              Pipeline (50KB) - Round-trip healing       │
├─────────────────────────────────────────────────────────┤
│             Catalog (K8s Schema Manager)                │
└─────────────────────────────────────────────────────────┘
```

**Key Files:**
- `engine.py` (48KB) - Main orchestration
- `pipeline.py` (50KB) - Lexer → Structurer → Analyzer → Healer
- `cross_resource.py` (21KB) - Graph-based analysis
- `best_practices.py` (14KB) - Resource limits, probes, tags

### Monokle Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Desktop IDE (Electron)                      │
│              VS Code Extension                           │
│              CLI (monokle validate)                      │
├─────────────────────────────────────────────────────────┤
│  Validation Engine   │  Resource Graph   │  Plugins     │
│  ├─ YAML Parser      │  ├─ Visualizer    │  ├─ OPA      │
│  ├─ Schema Validator │  ├─ Comparator    │  ├─ Custom   │
│  └─ Policy Engine    │  └─ Cluster API   │  └─ TypeScript│
├─────────────────────────────────────────────────────────┤
│            (Monokle Cloud - DISCONTINUED)               │
└─────────────────────────────────────────────────────────┘
```

---

## Strategic Analysis

### Monokle's Strengths (Where Yamlr is Behind)

| Strength | Impact | Yamlr Response |
|:--|:--|:--|
| **Desktop IDE** | Great for visual learners | Not competing here; CLI-first |
| **Graph Visualization** | See relationships visually | Add optional HTML report |
| **Helm/Kustomize Preview** | Render before commit | Add post-render validation |
| **VS Code Extension** | Mature, real-time | 🔴 P0 priority in roadmap |
| **Template Generation** | Low-code resource creation | Not core focus |

### Yamlr's Strengths (Where Monokle is Behind)

| Strength | Impact | Monokle Gap |
|:--|:--|:--|
| **Auto-Healing** | Fix, not just detect | ❌ No healing at all |
| **Commercial Support** | Enterprise confidence | ❌ Cloud discontinued |
| **Telemetry/ROI** | Prove value to execs | ❌ No telemetry story |
| **Freemium Model** | Land + expand motion | ❌ Pure OSS, no upsell |
| **Error → Fix Mapping** | Zero-knowledge UX | ❌ Just shows errors |
| **Performance at Scale** | 54 files/sec validated | Unknown |
| **Active Roadmap** | Control Plane vision | ❌ Minimal updates |

### Market Opportunity from Monokle Cloud EOL

> **Monokle Cloud was discontinued April 2024.** This creates a gap:
> - No centralized policy management
> - No team dashboards
> - No enterprise support

**Yamlr can capture:**
1. Teams who loved Monokle Cloud but need support
2. Teams who need healing, not just validation
3. Enterprise buyers who need SOC2/SLA

---

## Overlapping Capabilities (Similarities)

| Capability | Both Do This |
|:--|:--|
| **K8s Schema Validation** | Validate against OpenAPI specs |
| **Best Practice Checks** | Resource limits, probes, security |
| **OPA Policy Support** | Rego policies, Gatekeeper constraints |
| **Deprecation Detection** | Warn on outdated API versions |
| **CLI for CI/CD** | Both have `validate` commands |
| **SARIF Output** | Both integrate with GitHub security |
| **Cross-Resource Checks** | Both detect broken refs (Services→Pods) |

---

## Differentiation Summary

```
              DETECTION                    HEALING
                  │                           │
    ┌─────────────┴───────────────────────────┴─────────────┐
    │                                                        │
    │   Monokle ●────────────────────●                       │
    │           │ Validation │ IDE   │                       │
    │                                                        │
    │                        Yamlr ●─────────────────────●   │
    │                              │ Validation │ Healing │  │
    │                                                        │
    └────────────────────────────────────────────────────────┘
              GUI-FIRST                   CLI-FIRST
```

---

## Positioning Statement

**vs Monokle:**
> "Monokle shows you what's wrong. Yamlr fixes it. With Monokle Cloud discontinued, Yamlr is the only commercially-supported manifest quality tool with auto-healing."

**Messaging:**
1. "They validate. We heal."
2. "Monokle Cloud is gone. Yamlr is here."
3. "Same validation depth. Plus auto-fix. Plus enterprise support."

---

## Recommendations

### Immediate Priorities (Capture Monokle Cloud users)

| Action | Priority | Rationale |
|:--|:--:|:--|
| Ship VS Code Extension | 🔴 P0 | Match Monokle DX |
| Ship GitHub Actions | 🔴 P0 | Match Monokle CI/CD |
| Helm post-render validation | 🟡 P1 | Match Monokle Helm story |
| Highlight healing in marketing | 🔴 P0 | Key differentiator |

### Long-Term (Build moat)

| Action | Priority | Rationale |
|:--|:--:|:--|
| Telemetry Dashboard | 🔴 P0 | Fill Monokle Cloud gap |
| Team Policy Management | 🟡 P1 | Enterprise feature |
| SSO/SCIM | 🟡 P1 | Enterprise gate |
| Graph visualization (HTML) | 🟢 P2 | Nice-to-have, not core |

---

## Conclusion

| Dimension | Winner |
|:--|:--:|
| **Validation Depth** | Tie |
| **Healing** | **Yamlr** |
| **Visual Experience** | Monokle |
| **Commercial Viability** | **Yamlr** (Monokle Cloud EOL) |
| **Enterprise Roadmap** | **Yamlr** |
| **Developer UX** | Tie (different approaches) |

**Bottom Line:** Monokle and Yamlr are complementary more than competitive. Monokle is IDE-first for visual editing. Yamlr is CLI-first for automation and healing. With Monokle Cloud's discontinuation, Yamlr has a clear path to capture enterprise customers who need commercial support + healing.
