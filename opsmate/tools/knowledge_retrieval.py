from typing import List, Optional, Dict, Any

from pydantic import Field

from opsmate.knowledgestore.models import conn, aconn, config
from opsmate.dino.types import ToolCall, Message, PresentationMixin
from opsmate.dino.dino import dino
from pydantic import BaseModel
from typing import Union
import structlog
from jinja2 import Template
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)


class RretrievalResult(BaseModel):
    summary: str = Field(description="The summary of the knowledge")
    citations: List[str] = Field(
        description="The citations to the knowledge summary if any. Must be in the format of URL or file path"
    )


class KnowledgeNotFound(BaseModel):
    """
    This is a special case where the knowledge is not found.
    """


class KnowledgeRetrieval(ToolCall, PresentationMixin):
    """
    Knowledge retrieval tool allows you to search for relevant knowledge from the knowledge base.
    """

    _aconn = None
    _conn = None
    _embed_client = None
    query: str = Field(description="The query to search for")
    output: Optional[Union[RretrievalResult, KnowledgeNotFound]] = Field(
        description="The summarised output of the search - DO NOT POPULATE THIS FIELD",
        default=None,
    )

    async def __call__(self):
        logger.info("running knowledge retrieval tool", query=self.query)

        # XXX: sync based lancedb is more feature complete when it comes to query and reranks
        # however it comes with big penalty when it comes to latency
        # some of the features will land in 0.17.1+
        # conn = self.conn()

        # table = conn.open_table("knowledge_store")
        # results: List[KnowledgeStore] = (
        #     table.search(self.query, query_type="hybrid")
        #     .limit(10)
        #     .rerank(openai_reranker)
        #     .to_pydantic(KnowledgeStore)
        # )

        # if len(results) >= 5:
        #     results = results[:5]

        # results = [result.content for result in results]

        conn = await self.aconn()
        table = await conn.open_table("knowledge_store")
        results = (
            await table.query()
            # .nearest_to_text(self.query)
            .nearest_to(await self.embed(self.query))
            .select(["content", "data_source", "path", "metadata"])
            .limit(10)
            .to_list()
        )

        return await self.summary(self.query, results)

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
