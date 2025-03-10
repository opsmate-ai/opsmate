Opsmate out of box uses `openai/text-embedding-ada-002" for text embeddings, and no rerankers are being used during the retrieval.

That being said alternative embeddings and rerankers are available. This document outlines how to setup and use them.

## Embeddings

Opsmate supports two types of embeddings:

1. OpenAI embeddings
2. Sentence Transformers embeddings

### OpenAI embeddings

To explicitlyuse OpenAI embeddings, you need to set the following environment variables:

- `OPSMATE_EMBEDDING_REGISTRY_NAME=openai`
- `OPSMATE_EMBEDDING_MODEL_NAME=text-embedding-ada-002`

### Sentence Transformers embeddings

By default the sentence transformers is not installed. To install it, run:

=== "pip"
    ```bash
    pip install -U opsmate[sentence-transformers]
    ```

=== "pipx"
    ```bash
    pipx install opsmate[sentence-transformers] --force
    ```

Once installed, Opmsmate will automatically use the Sentence Transformers for embeddings.

You can explicitly specify the Sentence Transformers embeddings by setting the following environment variables:

- `OPSMATE_EMBEDDING_REGISTRY_NAME=sentence-transformers`
- `OPSMATE_EMBEDDING_MODEL_NAME=BAAI/bge-small-en-v1.5`

:warning: At the moment we do not officially support embedding models switch once the knowledge base is created. :warning:

To switch between embedding models, you need to delete the existing knowledge base and re-ingest.

## Rerankers

Opsmate supports the following rerankers:

1. RRF reranker
2. AnswerDotAI reranker
3. Cohere reranker
4. OpenAI reranker


### RRF reranker

To use the RRF reranker, you need to set the following environment variables:

- `OPSMATE_RERANKER_NAME=rrf`

### AnswerDotAI reranker

Out of box, the AnswerDotAI reranker is not installed. To install it, run:

=== "pip"
    ```bash
    pip install -U opsmate[reranker-answerdotai]
    ```

=== "pipx"
    ```bash
    pipx install opsmate[reranker-answerdotai] --force
    ```

To use the AnswerDotAI reranker, you need to set the following environment variables:

- `OPSMATE_RERANKER_NAME=answerdotai`

### Cohere reranker

Out of box, the Cohere reranker is not installed. To install it, run:

=== "pip"
    ```bash
    pip install -U opsmate[reranker-cohere]
    ```

=== "pipx"
    ```bash
    pipx install opsmate[reranker-cohere] --force
    ```

To use the Cohere reranker, you need to set the following environment variables:

- `OPSMATE_RERANKER_NAME=cohere`
- `COHERE_API_KEY=<your-cohere-api-key>`

### OpenAI reranker

To use the OpenAI reranker, you need to set the following environment variables:

- `OPSMATE_RERANKER_NAME=openai`
- `OPENAI_API_KEY=<your-openai-api-key>`
