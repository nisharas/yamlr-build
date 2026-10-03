# Python package build alias

The repository root is the canonical Yamlr Python package and release source.
This directory retains a secondary build manifest for tooling that expects a
package project under `python_wrapper/`; it builds from the same root Python
source and native Rust crate to keep the CLI entrypoint and SDK behavior in
sync.

For regular development and releases, build from the repository root. Both
projects produce the proprietary `yamlr` package.
