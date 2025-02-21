from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field, PrivateAttr
from typing import Optional, Any
from httpx import AsyncClient
from opsmate.dino import dino
from opsmate.dino.types import Message
from opsmate.tools.datetime import DatetimeRange, datetime_extraction
from opsmate.plugins import auto_discover
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

DEFAULT_ENDPOINT = "http://localhost:9090"
DEFAULT_PATH = "/api/v1/query_range"


class PromQuery(ToolCall[dict[str, Any]], DatetimeRange, PresentationMixin):
    """
    A tool to query metrics from Prometheus
    """

    query: str = Field(description="The prometheus query")
    step: str = Field(
        description="Query resolution step width in duration format or float number of seconds",
        default="15s",
    )
    y_label: str = Field(
        description="The y-axis label of the time series based on the query",
        default="Value",
    )
    x_label: str = Field(
        description="The x-axis label of the time series based on the query",
        default="Timestamp",
    )
    title: str = Field(
        description="The title of the time series based on the query",
        default="Time Series Data",
    )

    _client: AsyncClient = PrivateAttr(default_factory=AsyncClient)

    @property
    def headers(self):
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "opsmate prometheus tool",
        }

    async def __call__(self, context: dict[str, Any] = {}):
        endpoint = context.get("endpoint", DEFAULT_ENDPOINT)
        path = context.get("path", DEFAULT_PATH)

        response = await self._client.post(
            endpoint + path,
            data={
                "query": self.query,
                "start": self.start,
                "end": self.end,
                "step": self.step,
            },
            headers=self.headers,
        )
        return response.json()

    class Config:
        underscore_attrs_are_private = True

    def markdown(self): ...

    def time_series(self):
        values = self.output["data"]["result"][0]["values"]
        timestamps = [datetime.fromtimestamp(ts) for ts, _ in values]
        measurements = [float(val) for _, val in values]

        df = pd.DataFrame({"timestamp": timestamps, "measurement": measurements})
        plt.figure(figsize=(12, 6))
        plt.plot(df["timestamp"], df["measurement"], marker="o")
        plt.grid(True)
        plt.title(f"{self.title} - {self.query}")
        plt.xlabel(self.x_label)
        plt.ylabel(self.y_label)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()


@auto_discover(
    name="prometheus_query",
    description="A tool to query metrics from Prometheus",
    version="0.0.1",
    author="Micky",
)
@dino(
    model="gpt-4o",
    response_model=PromQuery,
    tools=[datetime_extraction],
)
async def prometheus_query(query: str, extra_context: str = ""):
    """
    You are a world class SRE who excels at querying metrics from Prometheus
    You are given a query in natural language and you need to convert it into a valid Prometheus query
    """
    return [
        Message.user(content=extra_context),
        Message.user(content=query),
    ]
