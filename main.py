from opsmate.knowledgestore.models import init_table
from opsmate.ingestions.fs import FsIngestion
from opsmate.textsplitters.markdown_header import MarkdownHeaderTextSplitter
from opsmate.ingestions.base import Chunk
from opsmate.dino import dino
from opsmate.dino.types import Message, ToolCall
from opsmate.tools import KnowledgeRetrieval, ShellCommand
from pydantic import BaseModel, Field, model_validator, ValidationInfo
from enum import Enum
from typing import List
import asyncio
import uuid


# class Summary(BaseModel):
#     summary: str = Field(description="The summary of the text")

#     @model_validator(mode="after")
#     def validate_brand(cls, v: str, info: ValidationInfo):
#         max_length = info.context.get("max_length")
#         if not max_length:
#             return v
#         if len(v.summary) > max_length:
#             raise ValueError(
#                 f"Summary must be less than {max_length} characters, actually length: {len(v.summary)}"
#             )
#         return v


# @dino(
#     model="gpt-4o-mini",
#     response_model=Summary,
#     context={"max_length": 100},
#     max_retries=3,
# )
# async def summarize(text: str, max_length: int = 100) -> Summary:
#     """
#     You are a world class expert in summarizing text.
#     Give an executive summary of the text into an one-sentence title under certain characters count.
#     """
#     return [
#         Message.user(text),
#         Message.assistant(
#             f"Summarise the text under {max_length} characters",
#         ),
#     ]


class Category(Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTENANCE = "maintenance"
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    PRODUCTION = "production"


@dino(
    model="gpt-4o-mini",
    response_model=List[Category],
)
async def categorize(text: str) -> str:
    f"""
    You are a world class expert in categorizing text.
    Please categorise the text into one or more unique categories:
    """
    return text


# async def summarize_chunk(chunk: Chunk):
#     summary = await summarize(chunk.content)
#     chunk.metadata["summary"] = summary.summary
#     return chunk


async def categorize_chunk(chunk: Chunk):
    categories = await categorize(chunk.content)
    chunk.metadata["categories"] = categories
    return chunk


@dino(
    model="gpt-4o",
    response_model=str,
    tools=[
        KnowledgeRetrieval,
        ShellCommand,
    ],
)
async def answer(question: str):
    """
    You are a world class expert in answering questions.
    Do not use command tools for knowledge retrieval.
    """
    return question


async def main():
    await init_table()

    # table = await db_conn.open_table("knowledge_store")

    # ingestor = FsIngestion(
    #     splitter=MarkdownHeaderTextSplitter(
    #         headers_to_split_on=[("#", "h1"), ("##", "h2")],
    #     ),
    #     local_path=".",
    #     glob_pattern="*.md",
    #     post_chunk_hooks=[categorize_chunk],
    # )

    # async for chunk in ingestor.ingest():
    #     categories = [cat.value for cat in chunk.metadata["categories"]]

    #     kb = {
    #         "uuid": str(uuid.uuid4()),
    #         # "summary": chunk.metadata["summary"],
    #         "data_source_provider": chunk.metadata["data_source_provider"],
    #         "data_source": chunk.metadata["data_source"],
    #         "path": chunk.metadata["path"],
    #         "categories": categories,
    #         "content": chunk.content,
    #     }
    #     await table.add([kb])

    result = await answer("how to install opsmate?")
    print(result)

    # result = await KnowledgeRetrieval(query="what is opsmate?")()
    # print(result)


if __name__ == "__main__":
    asyncio.run(main())
