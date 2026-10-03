# Stage 1: Build the Rust Native Core
FROM rust:1.98.1-slim-bookworm@sha256:ff521445a372125ed4f76e1453a1f8098f2d05332d1601d30db1c1f62757e730 AS builder
WORKDIR /app
COPY native_core ./native_core
RUN cargo build --locked --manifest-path native_core/Cargo.toml --release --bin yamlr

# Stage 2: Minimal Runtime
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/native_core/target/release/yamlr /usr/local/bin/yamlr
COPY actions/heal/entrypoint.sh /entrypoint.sh
COPY actions/stage_manifest_changes.sh /stage_manifest_changes.sh
RUN chmod +x /entrypoint.sh

WORKDIR /github/workspace
ENTRYPOINT ["/entrypoint.sh"]

LABEL maintainer="Yamlr Team"
LABEL version="1.0"
LABEL description="Autonomous Manifest Remediator (Compiled Native Version)"
