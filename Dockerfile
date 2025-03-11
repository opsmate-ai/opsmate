# Build stage
FROM python:3.12.3-slim-bullseye AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE /app/
COPY opsmate /app/opsmate
RUN uv build

# Final stage
FROM python:3.12.3-slim-bullseye

LABEL org.opencontainers.image.source=https://github.com/jingkaihe/opsmate

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

COPY --from=builder /app/dist/opsmate-*.whl /tmp/dist/

RUN pip install --no-cache-dir /tmp/dist/opsmate-*.whl

ENTRYPOINT ["opsmate"]
