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
  && pip install poetry==$POETRY_VERSION

WORKDIR /app

COPY poetry.lock pyproject.toml /app/
COPY opsmate /app/opsmate
COPY README.md /app/README.md


RUN poetry install --only main --no-interaction --no-ansi --no-root

ENTRYPOINT ["uvicorn", "opsmate.apiserver.apiserver:app", "--host", "0.0.0.0", "--port", "8000"]
