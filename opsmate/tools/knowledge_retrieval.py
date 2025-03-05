from typing import List, Dict, Any
from pydantic import Field
from lancedb.rerankers import OpenaiReranker, AnswerdotaiRerankers
from opsmate.knowledgestore.models import conn, aconn, config
from opsmate.dino.types import ToolCall, Message, PresentationMixin
from opsmate.dino.dino import dino
from pydantic import BaseModel
from typing import Union
import structlog
from jinja2 import Template
from openai import AsyncOpenAI
import time
from functools import wraps, cache

logger = structlog.get_logger(__name__)


def timer():
    def wrapper(f):
        @wraps(f)
        async def wrapped(*args, **kwargs):
            start = time.time()
            result = await f(*args, **kwargs)
            end = time.time()
            logger.info(
                "call completed",
                function=f"{f.__module__}.{f.__name__}",
                time=end - start,
            )
            return result

        return wrapped

    return wrapper


class RretrievalResult(BaseModel):
    summary: str = Field(description="The summary of the knowledge")
    citations: List[str] = Field(
        description="The citations to the knowledge summary if any. Must be in the format of URL or file path"
    )


class KnowledgeNotFound(BaseModel):
    """
    This is a special case where the knowledge is not found.
    """


@cache
def reranker():
    try:
        import transformers

        logger.info("using transformers reranker")
        return AnswerdotaiRerankers(column="content")
    except ImportError:
        logger.info("using openai reranker")
        return OpenaiReranker(column="content", model_name="gpt-4o-mini")


class KnowledgeRetrieval(
    ToolCall[Union[RretrievalResult, KnowledgeNotFound]], PresentationMixin
):
    """
    Knowledge retrieval tool allows you to search for relevant knowledge from the knowledge base.
    """

    _aconn = None
    _conn = None
    _embed_client = None
    query: str = Field(description="The query to search for")

    @timer()
    async def __call__(self, context: dict[str, Any] = {}):
        categories = context.get("categories", [])
        top_k = context.get("top_k", 50)
        top_n = context.get("top_n", 10)
        llm_summary = context.get("llm_summary", True)

        logger.info(
            "running knowledge retrieval tool",
            query=self.query,
            categories=categories,
            top_k=top_k,
            top_n=top_n,
            llm_summary=llm_summary,
        )
        conn = await self.aconn()
        table = await conn.open_table("knowledge_store")
        query = table.query()
        for category in categories:
            query = query.where(f"{category} in categories")
        results = (
            await query
            # .nearest_to_text(self.query)
            .nearest_to(await self.embed(self.query))
            .select(["content", "data_source", "path", "metadata"])
            .rerank(
                reranker=reranker(),
                query_string=self.query,
            )
            .limit(top_n)
            .to_list()
        )

        logger.info("reranked results", length=len(results))

        results = results[:top_n]
        if llm_summary:
            return await self.summary(self.query, results)
        else:
            result = RretrievalResult(
                summary="\n".join([result["content"] for result in results]),
                citations=[],
            )
            return result

    #
    async def embed(self, query: str):
        client = await self.embed_client()
        response = await client.embeddings.create(
            input=query, model=config.embedding_model_name
        )
        return response.data[0].embedding

    @dino(
        model="gpt-4o-mini",
        response_model=Union[RretrievalResult, KnowledgeNotFound],
    )
    async def summary(self, question: str, results: List[Dict[str, Any]]):
        """
        Given the following question and relevant knowledge snippets, provide a clear and
        comprehensive summary that directly addresses the question with citations to the source. Focus on synthesizing
        key information from the knowledge provided, maintaining accuracy, and presenting
        a cohesive response. If there are any gaps or contradictions in the provided
        knowledge, acknowledge them in your summary.

        If you are not sure about the answer, please respond with "knowledge not found".
        """

        context = "\n".join(
            f"""
            <knowledge {idx}>
                <metadata>
                {result["metadata"]}
                </metadata>
                <content>
                {result["content"]}
                </content>
            </knowledge {idx}>
            """
            for idx, result in enumerate(results)
        )

        return [
            Message.user(context),
            Message.user(question),
        ]

    def markdown(self):
        match self.output:
            case RretrievalResult():
                template = Template(
                    """
## Knowledge

{{ summary }}

{% if citations %}
### Citations

{% for citation in citations %}
- {{ citation }}
{% endfor %}
{% endif %}
"""
                )
                return template.render(
                    summary=self.output.summary, citations=self.output.citations
                )
            case KnowledgeNotFound():
                return "Knowledge not found"

    async def aconn(self):
        if not self._aconn:
            self._aconn = await aconn()
        return self._aconn

    def conn(self):
        if not self._conn:
            self._conn = conn()
        return self._conn

    async def embed_client(self):
        if not self._embed_client:
            self._embed_client = AsyncOpenAI()
        return self._embed_client
