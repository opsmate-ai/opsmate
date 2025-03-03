from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field, PrivateAttr, BaseModel
from typing import Any, List
from httpx import AsyncClient
from opsmate.dino import dino
from opsmate.dino.types import Message
from opsmate.tools.datetime import DatetimeRange, datetime_extraction
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import base64
from functools import lru_cache
from asyncio import Semaphore, create_task, gather

DEFAULT_ENDPOINT = "http://localhost:9090"
DEFAULT_PATH = "/api/v1/query_range"

DEFAULT_LABEL_BLACKLIST = (
    "pod",
    "container",
    "endpoint",
    "uuid",
    "uid",
    "id",
    "instance",
    "image",
    "name",
)


class PromQL:
    DEFAULT_LABEL_BLACKLIST = (
        "pod",
        "container",
        "endpoint",
        "uuid",
        "uid",
        "id",
        "instance",
        "image",
        "name",
    )

    def __init__(
        self,
        endpoint: str,
        user_id: str | None = None,
        api_key: str | None = None,
        client: AsyncClient = AsyncClient(),
    ):
        self.endpoint = endpoint
        self.user_id = user_id
        self.api_key = api_key
        self.client = client

    def metrics(
        self,
        force_reload=False,
        with_labels=True,
        label_blacklist=DEFAULT_LABEL_BLACKLIST,
    ):
        if force_reload or not hasattr(self, "df"):
            self.df = self.fetch_metrics(
                with_labels=with_labels, label_blacklist=label_blacklist
            )
            return self.df

        return self.df

    async def fetch_metrics(
        self, with_labels=True, label_blacklist=DEFAULT_LABEL_BLACKLIST
    ):
        response = await self.client.get(
            self.endpoint + "/api/v1/label/__name__/values", headers=self.headers()
        )
        print(self.headers())
        response_json = response.json()

        print(response_json)
        if response.status_code != 200:
            print("Failed to fetch metadata from prometheus")
            print(response_json)

        metrics_data = response_json["data"]

        metrics = []
        for metric in metrics_data:
            metrics.append({"metric_name": metric})

        print(metrics)
        semaphore = Semaphore(10)

        async def _apply_labels(metric):
            async with semaphore:
                metric["labels"] = await self.get_metric_labels(metric["metric_name"])
                return metric

        tasks = []
        for metric in metrics:
            tasks.append(create_task(_apply_labels(metric)))

        await gather(*tasks)

        df = pd.DataFrame(metrics)
        # df.rename(
        #     columns={
        #         "help": "description",
        #         "type": "metric_type",
        #     },
        #     inplace=True,
        # )

        self.df = df

        # df = pd.DataFrame(metrics)

        # df.rename(
        #     columns={
        #         "help": "description",
        #         "type": "metric_type",
        #     },
        #     inplace=True,
        # )

        # self.df = df

        # if with_labels:
        #     get_metric_labels = partial(
        #         self.get_metric_labels,
        #         label_blacklist=label_blacklist,
        #     )
        #     df["labels"] = df["metric_name"].apply(get_metric_labels)

        return df

    @lru_cache
    async def get_metric_labels(
        self, metric_name, label_blacklist=DEFAULT_LABEL_BLACKLIST
    ):
        response = await self.client.get(
            self.endpoint + "/api/v1/labels",
            params={"match[]": metric_name},
            headers=self.headers(),
        )
        response_json = response.json()
        if response.status_code != 200:
            print("Failed to fetch labels for metric: " + metric_name)
            return []
        labels = response_json["data"]
        labels.remove("__name__") if "__name__" in labels else None

        result = {}
        for label in labels:
            if label in label_blacklist:
                result[label] = ""
                continue
            response = await self.client.get(
                self.endpoint + "/api/v1/label/" + label + "/values",
                params={"match[]": metric_name},
                headers=self.headers(),
            )
            response_json = response.json()
            if response.status_code != 200:
                print("Failed to fetch values for label: " + label)
                result[label] = ""
                continue
            values = response_json["data"]
            result[label] = str.join("|", values)

        return result

    def headers(self):
        h = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "opsmate prometheus tool",
        }
        if self.user_id and self.api_key:
            b64_token = base64.b64encode(
                f"{self.user_id}:{self.api_key}".encode()
            ).decode()
            h["Authorization"] = f"Basic {b64_token}"
        return h


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

    def headers(self, context: dict[str, Any] = {}):
        h = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "opsmate prometheus tool",
        }
        if context.get("prometheus_api_key"):
            user_id = context.get("prometheus_user_id")
            token = context.get("prometheus_api_key")
            b64_token = base64.b64encode(f"{user_id}:{token}".encode()).decode()
            h["Authorization"] = f"Basic {b64_token}"
        return h

    async def __call__(self, context: dict[str, Any] = {}):
        endpoint = context.get("prometheus_endpoint", DEFAULT_ENDPOINT)
        path = context.get("prometheus_path", DEFAULT_PATH)

        response = await self._client.post(
            endpoint + path,
            data={
                "query": self.query,
                "start": self.start,
                "end": self.end,
                "step": self.step,
            },
            headers=self.headers(context),
        )
        return response.json()

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


class PrmetheusMetric(BaseModel):
    name: str = Field(
        description="The metric to use to answer the query, name of the metric only"
    )
    description: str = Field(description="A brief description of the metric")


@dino(
    model="claude-3-7-sonnet-20250219",
    response_model=List[PrmetheusMetric],
)
async def prometheus_metrics(query: str):
    """
    You are a world class SRE who excels at querying metrics from Prometheus
    You are given a query in natural language and you need decide what is the best metrics to use to answer the query

    Example:
    Query: "cpu usage of the cert manager deployment over the last 5 hours"
    Metrics: ["container_cpu_usage_seconds_total"]
    """
    return [
        Message.user(content=query),
    ]


@dino(
    model="claude-3-7-sonnet-20250219",
    response_model=PromQuery,
    tools=[datetime_extraction],
)
async def prometheus_query(query: str, extra_context: str = ""):
    """
    You are a world class SRE who excels at querying metrics from Prometheus
    You are given a query in natural language and you need to convert it into a valid Prometheus query

    <tasks>
    - Parse the natural language query
    - Genereate a PromQL query that fulfills the request
    - Provide a brief explanation of the query
    </tasks>

    <rules>
    - Use proper Prometheus functions and operators (rate, sum, by, on, etc.)
    - Consider performance implications of queries (cardinality, evaluation time)
    - Apply appropriate labels with proper interval to the query.
    - Use USE methods for computing resource usage metrics
    - Use RED methods for service level metrics
    </rules>
    """
    return [
        Message.user(content=extra_context),
        Message.user(content=query),
    ]
