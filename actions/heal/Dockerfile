# Stage 1: Build the native binary with Nuitka (Professional Edition)
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    clang \
    libpython3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy source code and requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt nuitka ordered-set

COPY . .

# Run the Nuitka build orchestrator for the PRO version
# This creates dist/yamlr_pro
RUN python scripts/build_nuitka.py --pro

# Stage 2: Create the minimal runtime image
FROM debian:bookworm-slim

# Install git for commit/push capabilities
RUN apt-get update && apt-get install -y \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the compiled Pro binary from the builder
COPY --from=builder /build/dist/yamlr_pro /usr/local/bin/yamlr

# Metadata
LABEL maintainer="Yamlr Team"
LABEL version="1.0"
LABEL description="Autonomous Manifest Repair (Professional Binary Version)"

# Entrypoint will handle git configuration if needed, then run yamlr heal
# For now, we point to a custom entrypoint script
COPY actions/heal/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
