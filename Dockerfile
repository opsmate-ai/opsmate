# Build stage
FROM python:3.12.3-slim-bullseye AS builder

ENV POETRY_VERSION=1.8.4 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

WORKDIR /app

# Install poetry and dependencies in one layer
COPY poetry.lock pyproject.toml /app/
RUN pip install --no-cache-dir poetry==$POETRY_VERSION && \
    poetry install --only main --no-interaction --no-ansi --no-root && \
    rm -rf $POETRY_CACHE_DIR

# Final stage
FROM python:3.12.3-slim-bullseye

# Install only kubectl without keeping unnecessary files
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl.sha256" && \
    echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl kubectl.sha256 && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only necessary files
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY opsmate /app/opsmate
COPY README.md /app/README.md

ENTRYPOINT ["uvicorn", "opsmate.apiserver.apiserver:app", "--host", "0.0.0.0", "--port", "8000"]
