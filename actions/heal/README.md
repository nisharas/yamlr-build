# 🩹 Yamlr Surgeon: Autonomous Manifest Repair

**Yamlr Surgeon** (`yamlr/heal`) previews fixes by default. Set `apply: 'true'` to modify manifests; set both `apply: 'true'` and `push: 'true'` to commit and push the repairs.

## 🧪 The "Slash Command" Experience

The Surgeon is designed for high-velocity platform teams. When configured, it monitors PRs for configuration drift or errors and provides a "Magic Moment" fix:

1. **Scan**: Identifies malformed YAML or security holes.
2. **Heal**: Natively repairs manifests using our **Professional C-Engine**.
3. **Commit**: Automatically commits the fixes with clear audit logs.
4. **Push**: Updates your PR branch instantly.

## 🛠️ Usage

```yaml
jobs:
  repair:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.PAT_TOKEN }} # Required for push
      - name: Yamlr Surgeon Repair
        uses: yamlr/heal@v1
        with:
          path: './k8s'
          apply: 'true'
          push: 'true'
```

## 🔒 Enterprise Security

The Surgeon runs the **Professional Edition** of the Yamlr engine, compiled natively for maximum IP protection and performance. Your manifests are processed locally in the runner—no data ever leaves your GitHub environment.

---
**Yamlr Surgeon: Stop finding problems. Start fixing them.**
