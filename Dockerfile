FROM python:3.12.3-slim-bullseye

ENV POETRY_VERSION=1.8.4 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry' \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random

RUN pip install --upgrade pip \
  && pip install poetry==$POETRY_VERSION && \
  apt-get update && apt-get install -y curl && \
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl.sha256" && \
  echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check && \
  install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
  rm kubectl.sha256

WORKDIR /app

COPY poetry.lock pyproject.toml /app/
COPY opsmate /app/opsmate
COPY README.md /app/README.md


RUN poetry install --only main --no-interaction --no-ansi --no-root

ENTRYPOINT ["uvicorn", "opsmate.apiserver.apiserver:app", "--host", "0.0.0.0", "--port", "8000"]
