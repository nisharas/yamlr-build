# Stage 1: Builder
# Uses full Python image to compile the binary
FROM python:3.11-slim as builder

WORKDIR /app

# Install build tools
RUN pip install --no-cache-dir pyinstaller

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY catalog/ catalog/

# Install dependencies
RUN pip install .

# Build binary
# Build binary
# Must match hack/build_binaries.py logic
RUN pyinstaller --noconfirm --onefile --clean \
    --name yamlr \
    --collect-all rich \
    --add-data "src/yamlr/core/data:yamlr/core/data" \
    --add-data "catalog:Yamlr/catalog" \
    src/yamlr/__main__.py

# Stage 2: Runner
# Using python-slim instead of distroless to allow shell execution (GitHub Actions)
FROM python:3.11-slim

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/dist/yamlr /usr/local/bin/yamlr

# Verify
COPY tools/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Verify
ENTRYPOINT ["/entrypoint.sh"]
