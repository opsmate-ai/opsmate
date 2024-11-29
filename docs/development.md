# Development

## Install dependencies

```bash
poetry install
```

## Running tests

```bash
poetry run pytest -n auto
```

## Install nodejs and openapi-generator-cli

```bash
# install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# install nodejs
nvm install --lts

npm install @openapitools/openapi-generator-cli -g
```
