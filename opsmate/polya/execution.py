import instructor
from anthropic import Anthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Union
import subprocess
from jinja2 import Template
from opsmate.polya.models import TaskPlan
import asyncio


async def execute(task_plan: TaskPlan):
    pass
