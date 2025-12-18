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


# Install dbt dependencies at build time (fail if missing dbt_project.yml)
RUN if [ -f /workspace/dbt/dbt_project.yml ]; then dbt deps --project-dir /workspace/dbt; else echo "No dbt_project.yml found, skipping dbt deps"; fi

# Set default command
CMD ["dbt", "--version"]