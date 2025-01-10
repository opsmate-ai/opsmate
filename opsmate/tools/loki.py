from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field, PrivateAttr
from typing import Literal, ClassVar, Optional
from httpx import AsyncClient
import os
import base64
from opsmate.dino import dino
from opsmate.dino.types import Message
from opsmate.tools.datetime import DatetimeRange, datetime_extraction


class LokiBase(ToolCall, PresentationMixin):
    """
    A tool to query logs in loki
    """

    user_id: ClassVar[str] = None
    auth_token: ClassVar[str] = None

    limit: int = Field(description="The number of results to return", default=100)
    direction: Literal["forward", "backward"] = Field(
        description="The direction of the search", default="forward"
    )
    output: Optional[str] = Field(
        description="The output of the loki query - DO NOT USE THIS FIELD",
        default=None,
    )

    _client: AsyncClient = PrivateAttr(default_factory=AsyncClient)

    def headers(self):
        base_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "opsmate loki tool",
        }
        user_id = self.user_id
        if not user_id:
            user_id = os.getenv("LOKI_USER_ID")

        if not user_id:
            return base_headers

        auth_token = self.auth_token
        if not auth_token:
            auth_token = os.getenv("LOKI_AUTH_TOKEN")

        if not auth_token:
            raise ValueError("LOKI_AUTH_TOKEN is not set")

        basic_auth = base64.b64encode(f"{user_id}:{auth_token}".encode()).decode()
        return {
            **base_headers,
            "Authorization": f"Basic {basic_auth}",
        }

    class Config:
        underscore_attrs_are_private = True

    def markdown(self): ...


class LokiMetrics(LokiBase):
    """
    A tool to query log-based metrics in loki
    """

    endpoint: ClassVar[str] = "http://localhost:3100"
    path: ClassVar[str] = "/api/v1/query"

    query: str = Field(description="The loki metrics based log query")

    async def __call__(self):
        response = await self._client.get(
            self.endpoint + self.path,
            params={
                "query": self.query,
                "limit": self.limit,
                "direction": self.direction,
            },
            headers=self.headers(),
        )

        return response.json()

    def markdown(self): ...


class LokiLogs(LokiBase, DatetimeRange):
    """
    A tool to query logs in loki
    """

    endpoint: ClassVar[str] = "http://localhost:3100"
    path: ClassVar[str] = "/api/v1/query_range"
    query: str = Field(description="The loki log query")

    async def __call__(self):
        response = await self._client.get(
            self.endpoint + self.path,
            params={
                "query": self.query,
                "start": self.start,
                "end": self.end,
                "limit": self.limit,
                "direction": self.direction,
            },
            headers=self.headers(),
        )
        return response.json()

    def markdown(self): ...


@dino(
    model="gpt-4o-mini",
    response_model=LokiLogs,
    tools=[datetime_extraction],
)
async def loki_logs(query: str, extra_context: str = ""):
    """
    You are a world class SRE who excels at querying logs in loki
    You are given a query in natural language and you need to convert it into a valid loki query

    <rules>
    * Use app_kubernetes_io_name to filter by the application name
    * Use namespace to filter by the namespace
    * Use pod to filter by the pod name
    * Use container to filter by the container name
    </rules>
    """
    return [
        Message.user(content=extra_context),
        Message.user(content=query),
    ]
