# Stage 1: Build the native binary with Nuitka
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    clang \
    libpython3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy source code and requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt nuitka ordered-set

COPY . .

# Run the Nuitka build orchestrator
# This creates dist/yamlr (Community Edition by default)
RUN python scripts/build_nuitka.py

# Stage 2: Create the minimal runtime image
FROM debian:bookworm-slim

# Install minimal runtime dependencies (if any, usually none for standalone)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the compiled binary from the builder
COPY --from=builder /build/dist/yamlr /usr/local/bin/yamlr

# Metadata
LABEL maintainer="Yamlr Team"
LABEL version="1.0"
LABEL description="Autonomous K8s Manifest Sentinel (Compiled Native Version)"

# Copy and use entrypoint script
COPY actions/scan/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
