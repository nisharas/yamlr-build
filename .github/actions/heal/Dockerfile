# Yamlr Action Runner (Google-Quality CI/CD)
FROM python:3.12-slim-bookworm

# 1. Install system dependencies if any (minimal for native binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Workspace
WORKDIR /github/workspace

# 3. Inject native binary (Assuming it was built in previous CI step or bundled)
# For the local action development, we copy the source and run via python. 
# For the official marketplace release, we will COPY the pre-built native binary.
COPY src/ /opt/yamlr/src/
COPY catalog/ /opt/yamlr/catalog/
ENV PYTHONPATH="/opt/yamlr/src"

# 4. Entrypoint
ENTRYPOINT ["python", "-m", "yamlr.cli.main"]
