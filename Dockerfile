# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install maturin and Rust
RUN apt-get update && apt-get install -y curl build-essential \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy project files
COPY . .

# Build wheels using maturin
RUN pip install --no-cache-dir maturin && \
    maturin build --release --strip

# Stage 2: Runner
FROM python:3.11-slim

WORKDIR /app

# Copy the built wheel from builder and install it
COPY --from=builder /app/target/wheels/*.whl .
RUN pip install *.whl && rm *.whl && \
    yamlr status

# Entrypoint
COPY tools/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
