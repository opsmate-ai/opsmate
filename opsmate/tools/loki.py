from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field, PrivateAttr
from typing import Literal, Any, Tuple, Dict, Union, List
from httpx import AsyncClient
import os
import base64
from opsmate.dino import dino
from opsmate.dino.types import Message, register_tool
from opsmate.tools.datetime import DatetimeRange, datetime_extraction
import pandas as pd
import structlog
from enum import Enum

logger = structlog.get_logger(__name__)

ResultType = Union[
    Tuple[Dict[str, Any], ...],
    List[Dict[str, Any]],
]


DEFAULT_ENDPOINT = "http://localhost:3100"
DEFAULT_PATH = "/api/v1/query_range"


class LogParser(str, Enum):
    LOGFMT = "logfmt"
    JSON = "json"
    UNKNOWN = "unknown"
    # REGEXP = "regexp"


# class LogFormat(str, Enum):
#     log_parser: LogParser = Field(description="The log parser to use")


@dino(
    model="claude-3-7-sonnet-20250219",
    response_model=LogParser,
)
async def log_format(logline: str, context: dict[str, Any] = {}):
    """
    You are a world class SRE who excels at parsing logs
    You are given a logline and you need to determine the log parser to use

    Example 1:
    logline: ts=2025-04-23T10:10:24.377036381Z level=info msg="rejoining peers
    return: LOGFMT

    Example 2:
    logline: {"ts":"2025-04-23T10:10:24.377036381Z","level":"info","msg":"rejoining peers"}
    return: JSON


    """
    # Example 3:
    # logline: 2025-04-23T10:10:24.377036381Z INFO:This is a log line
    # return: REGEXP
    return logline


class LokiQuery(ToolCall[ResultType], DatetimeRange, PresentationMixin):
    """
    A tool to query logs in loki
    """

    class Config:
        arbitrary_types_allowed = True

    query: str = Field(description="The query to execute")
    limit: int = Field(description="The number of results to return", default=100)
    direction: Literal["forward", "backward"] = Field(
        description="The direction of the search", default="forward"
    )
    log_parser: LogParser = Field(
        description="The log parser to use", default=LogParser.UNKNOWN
    )
    timeout: int = Field(
        default=30, ge=1, le=120, description="The timeout for the query in seconds"
    )

    def headers(self, context: dict[str, Any] = {}):
        h = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "opsmate loki tool",
        }
        if context.get("LOKI_API_KEY"):
            user_id = context.get("LOKI_USER_ID")
            token = context.get("LOKI_API_KEY")
            b64_token = base64.b64encode(f"{user_id}:{token}".encode()).decode()
            h["Authorization"] = f"Basic {b64_token}"
        return h

    async def __call__(self, context: dict[str, Any] = {}):
        # XXX: TBD whether we want to make the envvar injection the default behaviour
        context = context.copy()
        envvars = os.environ.copy()
        context.update(envvars)

        endpoint = context.get("LOKI_ENDPOINT", DEFAULT_ENDPOINT)
        path = context.get("LOKI_PATH", DEFAULT_PATH)

        if self.log_parser == LogParser.UNKNOWN:
            self.log_parser = await self.determine_log_parser(context)
            if self.log_parser != LogParser.UNKNOWN:
                self.query = f"{self.query} | {self.log_parser.value}"

        response = await AsyncClient().post(
            endpoint + path,
            data={
                "query": self.query,
                "start": self.start,
                "end": self.end,
                "limit": self.limit,
                "direction": self.direction,
            },
            headers=self.headers(context),
        )

        if response.status_code != 200:
            logger.error(
                "Failed to fetch logs from loki", response_json=response.json()
            )
            return [
                {
                    "error": "Failed to fetch logs from loki",
                    "data": response.text,
                }
            ]

        result = response.json()["data"]["result"]

        result = [item["stream"] for item in result]

        return result

    async def determine_log_parser(self, context: dict[str, Any] = {}):
        endpoint = context.get("LOKI_ENDPOINT", DEFAULT_ENDPOINT)
        path = context.get("LOKI_PATH", DEFAULT_PATH)

        response = await AsyncClient().post(
            endpoint + path,
            data={
                "query": self.query,
                "start": self.start,
                "end": self.end,
                "limit": 10,
                "direction": self.direction,
            },
            headers=self.headers(context),
        )

        if response.status_code != 200:
            logger.error(
                "Failed to fetch logs from loki", response_json=response.json()
            )
            return {
                "error": "Failed to fetch logs from loki",
                "data": response.text,
            }

        result = response.json()["data"]["result"]
        if len(result) == 0:
            return LogParser.UNKNOWN
        result = result[0]

        values = "\n".join([item[1] for item in result["values"]])

        # print(values)
        return await log_format(values, context)

    _dataframe: pd.DataFrame | None = PrivateAttr(default=None)

    @property
    def dataframe(self):
        if self._dataframe is not None:
            return self._dataframe

        self._dataframe = pd.DataFrame(self.output)
        return self._dataframe

    def markdown(self, context: dict[str, Any] = {}):
        return f"""
## Loki Query

```
{self.query}
```

## Result

{self.dataframe.to_markdown()}
"""

    def prompt_display(self):
        # sample the dataframe
        df = self.dataframe.sample(20, replace=True)
        return f"""
## Loki Query

Start: {self.start}
End: {self.end}

```
{self.query}
```

## Result (sampled 20 rows)

{df.to_markdown()}
"""


@dino(
    model="claude-3-7-sonnet-20250219",
    response_model=LokiQuery,
    tools=[datetime_extraction],
)
async def loki_query(query: str, context: dict[str, Any] = {}):
    """
    You are a world class SRE who excels at querying logs in loki
    You are given a query in natural language and you need to convert it into a valid loki query

    <rules>
    * Before query please confirm the namespace(s) and container(s), and optionally the pod(s) from the query
    * Use namespace to filter by the namespace
    * Use pod to filter by the pod name
    * Use container to filter by the container name
    * regex can be used for filtering
    * For structured log if the log parser and fields are determined, you can further filter the log by fields e.g. `{app_kubernetes_io_name="my-app"} | logfmt | path="/api/v1/users"`
    * Do not use double curly braces `{{ }}` in the query
    </rules>
    """

    return [
        Message.user(query),
    ]


@register_tool()
class LokiQueryTool(ToolCall[LokiQuery], PresentationMixin):
    """
    A tool to query logs in loki

    <rules>
    * Please use this instead of the `kubectl logs` command
    * If you can please specify the namespace, pod, container of the subject that you are interested in
    * You don't need to worry about whether loki is running
    * If you know the format of the log pass the log format to the tool, e.g. `logfmt` or `json`
    </rules>
    """

    natural_language_query: str = Field(
        description="The natural language query to be translated into a loki query"
    )

    async def __call__(self, context: dict[str, Any] = {}):
        model = context.get("dino_model", "claude-3-7-sonnet-20250219")
        query: LokiQuery = await loki_query(
            self.natural_language_query,
            context=context,
            model=model,
        )

        try:
            await query.run(context)
        except Exception as e:
            logger.error("Failed to query loki", error=e)
            query.output = [
                {
                    "error": "Failed to query loki",
                    "data": str(e),
                }
            ]
        if len(query.output) == 0:
            query.output = [
                {
                    "error": "No logs found",
                    "data": "No logs found",
                }
            ]
        return query

    def markdown(self, context: dict[str, Any] = {}):
        return self.output.markdown()

    def error(self):
        output = self.output
        query_output = output.output

        if not isinstance(query_output, list) and not isinstance(query_output, tuple):
            return False
        if len(query_output) > 0 and "error" in query_output[0]:
            return True
        return False

    def prompt_display(self):
        try:
            if self.error():
                return self.output.markdown()
            return self.output.prompt_display()
        except Exception as e:
            logger.error("Failed to display prompt", error=e)
            return "Failed to display prompt"
