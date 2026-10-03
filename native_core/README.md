# Yamlr Native Core (Rust)

This directory contains the high-performance Rust core of the Yamlr Engine. It provides ultra-fast YAML sharding, identity extraction, and cross-resource graph building.

## Architecture

- **`src/lib.rs`**: The main entry point and PyO3 bridge.
- **`NativeShard`**: Tokenized YAML sharding logic.
- **`NativeIdentity`**: Fast-path K8s resource identification.
- **`NativeEdge`**: Parallel graph building using the Rayon crate.

## Build Instructions

To build the native extension:

### Prerequisites
- Rust Toolchain (stable)
- Python 3.10+
- `pip install maturin`

### Standard Build (Development)
```bash
# Builds and installs into the current virtualenv
maturin develop
```

### Production Build (Release)
```bash
# Generates high-performance optimized binaries
maturin build --release
```

### Performance Notes
The native core uses **Parallel Data Processing** via the `rayon` crate. It is designed to handle large manifest sets without memory exhaustion by utilizing streaming parsing and immutable identity sharing.

---
**Author**: Nishar A Sunkesala / Yamlr Team
**License**: Proprietary. See [the Yamlr license](../LICENSE).
