# Dockerfile for dbt-trino
# Build locally to avoid registry issues

FROM python:3.11-slim

WORKDIR /workspace/dbt

# Install git and dbt-trino
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
    dbt-trino==1.8.2

# Set default command
CMD ["dbt", "--version"]