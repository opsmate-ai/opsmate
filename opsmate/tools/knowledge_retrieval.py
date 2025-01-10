from typing import List, Optional

from pydantic import Field

from opsmate.knowledgestore.models import KnowledgeStore, openai_reranker, conn, aconn
from opsmate.dino.types import ToolCall, Message, PresentationMixin
from opsmate.dino.dino import dino
import structlog

logger = structlog.get_logger(__name__)


class KnowledgeRetrieval(ToolCall, PresentationMixin):
    """
    Knowledge retrieval tool allows you to search for relevant knowledge from the knowledge base.
    """

    _aconn = None
    _conn = None
    query: str = Field(description="The query to search for")
    output: Optional[str] = Field(
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
            .nearest_to_text(self.query)
            .select(["content"])
            .to_list()
        )  # .limit(10).to_list()
        results = [result["content"] for result in results]

        return await self.summary(self.query, results)

    @dino(
        model="gpt-4o-mini",
        response_model=str,
    )
    async def summary(self, question: str, results: List[str]):
        """
        Given the following question and relevant knowledge snippets, provide a clear and
        comprehensive summary that directly addresses the question. Focus on synthesizing
        key information from the knowledge provided, maintaining accuracy, and presenting
        a cohesive response. If there are any gaps or contradictions in the provided
        knowledge, acknowledge them in your summary.

        If you are not sure about the answer, please respond with "knowledge not found".
        """
        context = "\n".join(
            f"""
            <knowledge {idx}>
            {result}
            </knowledge {idx}>
            """
            for idx, result in enumerate(results)
        )
        return [
            Message.user(context),
            Message.user(question),
        ]

    def markdown(self):
        return f"""
### Knowledge

{self.output}
"""

    async def aconn(self):
        if not self._aconn:
            self._aconn = await aconn()
        return self._aconn

    def conn(self):
        if not self._conn:
            self._conn = conn()
        return self._conn
