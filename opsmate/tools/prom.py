from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field, PrivateAttr, computed_field
from typing import Any
from httpx import AsyncClient
from opsmate.dino import dino
from opsmate.dino.types import Message
from opsmate.tools.datetime import DatetimeRange, datetime_extraction
from opsmate.tools.knowledge_retrieval import KnowledgeRetrieval
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotext
from datetime import datetime
import base64
from functools import lru_cache
from asyncio import Semaphore, create_task, gather
import structlog

logger = structlog.get_logger(__name__)
DEFAULT_ENDPOINT = "http://localhost:9090"
DEFAULT_PATH = "/api/v1/query_range"


class PromQL:
    DEFAULT_LABEL_BLACKLIST = (
        "pod",
        "container",
        "container_id",
        "endpoint",
        "uuid",
        "uid",
        "id",
        "instance",
        "image",
        "name",
        "mountpoint",
        "device",
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
        response_json = response.json()

        if response.status_code != 200:
            logger.error(
                "Failed to fetch metrics from prometheus", response_json=response_json
            )
            raise Exception("Failed to fetch metrics from prometheus")

        metrics_data = response_json["data"]

        metrics = []
        for metric in metrics_data:
            metrics.append({"metric_name": metric})

        semaphore = Semaphore(10)

        async def _apply_labels(metric):
            async with semaphore:
                metric["labels"] = await self.get_metric_labels(
                    metric["metric_name"], label_blacklist=label_blacklist
                )
                return metric

        tasks = []
        for metric in metrics:
            tasks.append(create_task(_apply_labels(metric)))

        await gather(*tasks)

        return metrics

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
            logger.error(
                "Failed to fetch labels for metric: " + metric_name,
                response_json=response_json,
            )
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
                logger.error(
                    "Failed to fetch values for label: " + label,
                    response_json=response_json,
                )
                result[label] = ""
                continue
            values = response_json["data"]
            # result[label] = str.join("|", values)
            joint_values = "|".join(values)
            if len(joint_values) > 100:
                result[label] = joint_values[:100] + "..."
            else:
                result[label] = joint_values

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
    explanation: str = Field(
        description="A brief explanation of the query",
    )

    _client: AsyncClient = PrivateAttr(default_factory=AsyncClient)

    @computed_field
    def step(self) -> str:
        # no more than 10,000 points
        secs = (self.end_dt - self.start_dt).total_seconds() / 10000
        if secs < 1:
            return "15s"
        else:
            return f"{int(secs)}s"

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

    def time_series(self, in_terminal: bool = False):

        logger.info("plotting time series", query=self.query)
        plt.figure(figsize=(12, 6))

        for result in self.output["data"]["result"]:
            values = result["values"]
            metric = result["metric"]
            metric_name = "-".join(metric.values())
            timestamps = [datetime.fromtimestamp(ts) for ts, _ in values]
            measurements = [float(val) for _, val in values]
            df = pd.DataFrame({"timestamp": timestamps, "measurement": measurements})
            if in_terminal:
                df["timestamp"] = mdates.date2num(df["timestamp"])
            plt.plot(df["timestamp"], df["measurement"], label=metric_name)
        plt.grid(True)
        plt.title(f"{self.title} - {self.query}")
        plt.xlabel(self.x_label)
        plt.ylabel(self.y_label)
        plt.xticks(rotation=45)
        plt.legend(bbox_to_anchor=(0.5, -0.15), loc="upper center", ncol=2)
        plt.tight_layout()

        if in_terminal:
            plt.show(block=False)
            fig = plt.gcf()
            plotext.from_matplotlib(fig)
            plotext.show()
        else:
            plt.show()


# class PrometheusMetric(BaseModel):
#     name: str = Field(
#         description="The metric to use to answer the query, name of the metric only"
#     )
#     labels: Dict[str, str] = Field(
#         description="the relevant label key value pairs to use to answer the query"
#     )
#     description: str = Field(
#         description="A brief description of the metric",
#         max_length=100,
#     )

#     def markdown(self):
#         return f"""
# <metric>
# name: {self.name}
# description: {self.description}
# labels: {self.labels}
# </metric>
# """


# @dino(
#     model="claude-3-7-sonnet-20250219",
#     tools=[KnowledgeRetrieval],
#     response_model=List[PrometheusMetric],
# )
# async def prometheus_metrics(query: str, context: dict[str, Any] = {}):
#     """
#     You are a world class SRE who excels at querying metrics from Prometheus
#     You are given a query in natural language and you need decide what is the best metrics to use to answer the query

#     <important>
#     * **DO NOT** make up labels that do not belong to the metric.
#     * You can only use the KnowledgeRetrieval tool call no more than 2 times.
#     * Narrow down the metrics with labels such as cluster, job, namespace, etc if possible.
#     </important>

#     Example:
#     Query: "cpu usage of the cert manager deployment over the last 5 hours"
#     Metrics: ["container_cpu_usage_seconds_total"]
#     Labels: {"cluster": "the-cluster-name", "job": "cert-manager"}
#     """
#     return [
#         Message.user(content=query),
#     ]


@dino(
    model="claude-3-7-sonnet-20250219",
    response_model=PromQuery,
    tools=[datetime_extraction, KnowledgeRetrieval],
)
async def prometheus_query(query: str, context: dict[str, Any] = {}):
    """
    You are a world class SRE who excels at querying metrics from Prometheus
    You are given a query in natural language and you need to convert it into a valid Prometheus query
    Please think carefully and generate 3 different PromQL queries, and then choose the best one among them as the answer.

    <tasks>
    - Parse the natural language query
    - Genereate a PromQL query that fulfills the request
    - Provide a brief explanation of the query
    </tasks>

    <important>
    - use `datetime_extraction` tool to get the time range of the query
    - use `KnowledgeRetrieval` tool to get the metrics and labels that are relevant to the query
    - In the query, DO NOT use labels that are not present in the metrics from knowledge retrieval.
    - DO NOT use metrics that do not exist from knowledge retrieval.
    - USE `_bucket` suffix metrics if the query is about histograms.
    </important>
    """

    return [
        Message.user(query),
    ]
