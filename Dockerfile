# Build image
FROM python:3.9-slim AS builder

RUN apt-get update && apt-get install -y locales libcurl4-openssl-dev libssl-dev curl && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app/

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN curl -sLo /tmp/uv.tar.gz https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz \
 && tar -xvf /tmp/uv.tar.gz -C /usr/bin --strip-components=1

# Install dependencies
# Run this separately to benefit from docker cache for dependencies
COPY pyproject.toml uv.lock /app/
RUN uv sync --no-dev

# Install the app
COPY . /app/
RUN uv sync --no-dev

# Production image
FROM python:3.9-slim
WORKDIR /app/
COPY --from=builder /app/ .

ENTRYPOINT ["/app/.venv/bin/cinder-snapshooter"]
