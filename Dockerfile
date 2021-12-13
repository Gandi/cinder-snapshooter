# Build image
FROM python:3.9-slim AS builder

RUN apt-get update && apt-get install -y locales libcurl4-openssl-dev libssl-dev curl && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app/

# Install poetry
ENV POETRY_HOME=/opt/poetry PATH="/opt/poetry/bin:${PATH}"
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
# Run this separately to benefit from docker cache for dependencies
COPY pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.in-project true && poetry install --no-interaction --no-root --no-dev

# Install the app
COPY . /app/
RUN poetry install --no-interaction --no-dev

# Production image
FROM python:3.9-slim
WORKDIR /app/
COPY --from=builder /app/ .

ENTRYPOINT ["/app/.venv/bin/cinder-snapshooter"]