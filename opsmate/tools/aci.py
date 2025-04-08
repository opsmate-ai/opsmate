from opsmate.dino.types import ToolCall, PresentationMixin, register_tool
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Dict, List, Optional, ClassVar, Self, Any
from collections import defaultdict
from pathlib import Path
from opsmate.tools.utils import maybe_truncate_text
from opsmate.dino import dino
import asyncio
import os
import structlog
import traceback
import re
from jinja2 import Template

logger = structlog.get_logger(__name__)

PATTERN_NOT_FOUND = "Pattern not found"


class Result(BaseModel):
    """
    Result is a model that represents the result of a tool call.
    """

    output: Optional[str] = Field(
        description="The output of the tool call",
        default=None,
    )
    error: Optional[str] = Field(
        description="The error of the tool call",
        default=None,
    )

    operation: Optional[str] = Field(
        description="The operation that is being performed",
        default=None,
    )

    path: Optional[str] = Field(
        description="The path of the file or directory to be operated on",
        default=None,
    )

    old_content: Optional[str] = Field(
        description="The old content to be replaced by the new content",
        default=None,
    )

    content: Optional[str] = Field(
        description="The new content that is being operated on",
        default=None,
    )

    insert_line_number: Optional[int] = Field(
        description="The line number to insert the content at, only applicable for the `insert` action. Note the line number is 0-indexed.",
        default=None,
    )

    line_start: Optional[int] = Field(
        description="The start line number to be operated on, only applicable for the 'update' action. Note the line number is 0-indexed.",
        default=None,
    )
    line_end: Optional[int] = Field(
        description="The end line number to be operated on, only applicable for the 'update' action. Note the line number is 0-indexed.",
        default=None,
    )


@register_tool()
class ACITool(ToolCall[Result], PresentationMixin):
    """
    ACITool is a text editor built for AI Agents to search, view, create, update,
    insert and undo file operations.
    DO NOT use ACITool for the purpose of knowledge retrieval.
    """

    model_config = ConfigDict(populate_by_name=True)

    _file_history: ClassVar[Dict[Path, List[str]]] = defaultdict(list)

    # number of lines before and after the match
    search_context_window: ClassVar[int] = 4

    action: str = Field(
        description="The action to take for text editing or searching",
        choices=["search", "view", "create", "update", "insert", "undo"],
    )

    path: str = Field(description="The path of the file or directory to be operated on")

    insert_line_number: Optional[int] = Field(
        description="The line number to insert the content at, only applicable for the `insert` action. Note the line number is 0-indexed.",
        default=None,
    )

    line_start: Optional[int] = Field(
        description="The start line number to be operated on, only applicable to the 'view' and 'update' actions. Note the line number is 0-indexed.",
        default=None,
    )
    line_end: Optional[int] = Field(
        description="The end line number to be operated on, only applicable to the 'view' and 'update' actions. Note the line number is 0-indexed.",
        default=None,
    )

    content: Optional[str] = Field(
        description="The content to be added to the file, only applicable for the `search`, `create`, `update` and `insert` actions.",
        default=None,
        alias="new_content",  # llm sometimes uses new_content instead of content and cannot be persuaded, thus create an alias
    )

    old_content: Optional[str] = Field(
        description="The old content to be replaced by the new content, only applicable for the `update` action.",
        default=None,
    )

    @model_validator(mode="after")
    def validate_path(self) -> Self:
        if self.action != "create":
            if not Path(self.path).exists():
                raise ValueError(f"File or directory {self.path} does not exist")
        else:
            if Path(self.path).exists():
                raise ValueError(f"File or directory {self.path} already exists")
        return self

    @model_validator(mode="after")
    def validate_search_action(self) -> Self:
        if self.action == "search":
            if self.content is None:
                self.content = ""
        return self

    @model_validator(mode="after")
    def validate_view_action(self) -> Self:
        if self.action == "view":
            if self.line_start is None and self.line_end is not None:
                raise ValueError("line_start is required when line_end is provided")
            if self.line_end is None and self.line_start is not None:
                raise ValueError("line_end is required when line_start is provided")

            if self.line_start is not None and self.line_end is not None:
                if self.line_start < 0 or self.line_end < self.line_start:
                    raise ValueError(
                        "line_end must be greater than or equal to line_start"
                    )

        return self

    @model_validator(mode="after")
    def validate_create_action(self) -> Self:
        if self.action == "create":
            if self.content is None:
                raise ValueError("content is required for the create action")
        return self

    @model_validator(mode="after")
    def validate_update_action(self) -> Self:
        if self.action == "update":
            if self.old_content is None:
                raise ValueError("old_content is required for the update action")
            if self.content is None:
                raise ValueError("content is required for the update action")
        return self

    @model_validator(mode="after")
    def validate_insert_action(self) -> Self:
        if self.action == "insert":
            if self.content is None:
                raise ValueError("content is required for the insert action")
            if self.insert_line_number is None:
                raise ValueError("insert_line_number is required for the insert action")
        return self

    @model_validator(mode="after")
    def validate_undo_action(self) -> Self:
        if self.action == "undo":
            if self.path is None:
                raise ValueError("path is required for the undo action")
        return self

    async def __call__(self) -> Result:
        logger.info(
            "executing action",
            action=self.action,
            path=self.path,
            content=self.content,
            old_content=self.old_content,
            insert_line_number=self.insert_line_number,
            line_start=self.line_start,
            line_end=self.line_end,
        )
        if self.action == "search":
            return await self.search()
        elif self.action == "view":
            return await self.view()
        elif self.action == "create":
            return await self.create()
        elif self.action == "update":
            return await self.update()
        elif self.action == "insert":
            return await self.insert()
        elif self.action == "undo":
            return await self.undo()
        else:
            raise ValueError(f"Invalid action: {self.action}")

    async def create(self) -> Result:
        try:
            Path(self.path).write_text(self.content)
            self._file_history[Path(self.path)].append(self.content)
        except Exception as e:
            return Result(
                error=str(e),
                operation="create",
                path=self.path,
                content=self.content,
            )
        return Result(
            output="File created successfully",
            operation="create",
            path=self.path,
            content=self.content,
        )

    async def view(self) -> Result:
        if Path(self.path).is_file():
            return await self._view_file()
        elif Path(self.path).is_dir():
            return await self._view_directory()
        else:
            return Result(
                error=f"The path {self.path} is not a file or directory",
                operation="view",
                path=self.path,
            )

    async def _view_file(self) -> Result:
        try:
            with open(self.path, "r") as f:
                lines = f.readlines()

            # Handle line range if specified
            if self.line_start is not None and self.line_end is not None:
                if self.line_end >= len(lines):
                    raise ValueError(
                        f"end line number {self.line_end} is out of range (file has {len(lines)} lines)"
                    )
                lines = lines[self.line_start : self.line_end + 1]

            # Format lines with line numbers (0-indexed)
            numbered_contents = ""
            for i, line in enumerate(lines):
                line_number = i if self.line_start is None else i + self.line_start
                numbered_contents += f"{line_number:4d} | {line}"

            return Result(
                output=maybe_truncate_text(numbered_contents),
                operation="view",
                path=self.path,
            )
        except Exception as e:
            return Result(
                error=f"Failed to view file: {e}",
                operation="view",
                path=self.path,
            )

    async def _view_directory(self) -> Result:
        try:
            process = await asyncio.create_subprocess_shell(
                rf"find {self.path} -maxdepth 2 -not -path '*/\.*' -not -name '.*' | sort",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            # Add 5 second timeout to communicate
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
            return Result(
                output=maybe_truncate_text(stdout.decode()),
                operation="view",
                path=self.path,
            )
        except asyncio.TimeoutError:
            # Kill the process if it times out
            process.kill()
            return Result(
                error="Directory listing timed out after 5 seconds",
                operation="view",
                path=self.path,
            )
        except Exception as e:
            return Result(
                error=f"Failed to view directory: {e}",
                operation="view",
                path=self.path,
            )

    async def insert(self) -> Result:
        """
        Insert content into a file at a specific line number.
        """
        try:
            with open(self.path, "r") as f:
                lines = [line.rstrip() for line in f.readlines()]
            if self.insert_line_number < 0 or self.insert_line_number >= len(lines):
                raise ValueError(
                    f"end line number {self.insert_line_number} is out of range (file has {len(lines)} lines)"
                )
            lines.insert(self.insert_line_number, self.content)

            new_content = "\n".join(lines)
            Path(self.path).write_text(new_content)
            self._file_history[Path(self.path)].append(new_content)

            return Result(
                output="Content inserted successfully",
                operation="insert",
                path=self.path,
                content=self.content,
                insert_line_number=self.insert_line_number,
            )
        except Exception as e:
            return Result(
                error=f"Failed to insert content into file: {e}",
                operation="insert",
                path=self.path,
                content=self.content,
                insert_line_number=self.insert_line_number,
            )

    async def update(self) -> Result:
        """
        Replace the old content with the new content within a specified line range.
        """
        path = Path(self.path)
        file_content = path.read_text()
        lines = file_content.splitlines()

        # Determine the range of lines to operate on
        start = self.line_start if self.line_start is not None else 0
        end = self.line_end if self.line_end is not None else len(lines) - 1

        if self.old_content is None or self.old_content == "":
            return Result(
                error="Old content cannot be empty",
                operation="update",
                path=self.path,
                old_content=self.old_content,
                content=self.content,
                line_start=start,
                line_end=end,
            )

        # Validate line range
        if start < 0 or end >= len(lines) or start > end:
            return Result(
                error="Invalid line range specified",
                operation="update",
                path=self.path,
                old_content=self.old_content,
                line_start=start,
                line_end=end,
            )

        # Join the lines within the specified range
        range_content = "\n".join(lines[start : end + 1])

        # Check for occurrences within the specified range
        occurrences = range_content.count(self.old_content)
        if occurrences == 0:
            return Result(
                error="Old content not found in the specified line range",
                operation="update",
                path=self.path,
                old_content=self.old_content,
                line_start=start,
                line_end=end,
            )
        elif occurrences > 1:
            return Result(
                error="Old content occurs more than once in the specified line range, please make sure its uniqueness",
                operation="update",
                path=self.path,
                old_content=self.old_content,
                line_start=start,
                line_end=end,
            )

        # Replace the old content with the new content within the range
        updated_range_content = range_content.replace(self.old_content, self.content)

        # Update the lines with the modified content
        lines[start : end + 1] = updated_range_content.splitlines()

        # Write the updated content back to the file
        new_file_content = "\n".join(lines)
        path.write_text(new_file_content)
        self._file_history[path].append(new_file_content)

        return Result(
            output="Content updated successfully",
            operation="update",
            path=self.path,
        )

    async def undo(self) -> Result:
        """
        Undo the last file operation.
        """
        path = Path(self.path)
        if len(self._file_history[path]) <= 1:
            return Result(
                error="There is no history of file operations",
                operation="undo",
                path=self.path,
            )
        self._file_history[path].pop()
        latest_content = self._file_history[path][-1]
        path.write_text(latest_content)
        return Result(
            output="File rolled back to previous state",
            operation="undo",
            path=self.path,
        )

    async def search(self) -> Result:
        """
        Search for a pattern in a file or directory using regex.
        """
        path = self.path
        if path == ".":
            path = os.getcwd()
        path_type_check = Path(path)
        logger.info("searching", path=path, content=self.content)
        try:
            if path_type_check.is_file():
                result = await self._search_file(path)
                return Result(output=maybe_truncate_text(result))

            elif path_type_check.is_dir():
                results = ""
                for root, _dirs, files in os.walk(path):
                    for file in files:
                        if file.startswith(".") or root.startswith("."):
                            continue
                        result = await self._search_file(os.path.join(root, file))
                        if result and result != PATTERN_NOT_FOUND:
                            results += f"{root}/{file}\n---\n{result}\n"
                logger.info("search results", results=results)
                return Result(
                    output=maybe_truncate_text(results),
                    operation="search",
                    path=self.path,
                    content=self.content,
                )

            else:
                return Result(
                    error=f"Path {path} is not a file or directory",
                    operation="search",
                    path=self.path,
                    content=self.content,
                )

        except asyncio.TimeoutError:
            return Result(
                error="Search timed out after 5 seconds",
                operation="search",
                path=self.path,
                content=self.content,
            )
        except Exception as e:
            return Result(
                error=f"Failed to search: {e}",
                operation="search",
                path=self.path,
                content=self.content,
            )

    async def _search_file(self, filename: str) -> str:
        try:
            cmd = f"grep -En -A {self.search_context_window} -B {self.search_context_window} '{self.content}' {filename}"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
            result = stdout.decode().strip()

            if not result:
                return PATTERN_NOT_FOUND

            formatted_lines = []
            for line in result.splitlines():
                # Skip grep's separator lines and error messages
                if line.startswith("--") or line.startswith("grep:"):
                    continue

                # Use regex match instead of split for more reliable parsing
                match = re.match(r"^(\d+)([-:])(.*?)$", line)
                if match:
                    line_num, sep, content = match.groups()
                    try:
                        line_num = int(line_num)
                        if sep == ":":
                            sep = "|"
                        formatted_lines.append(
                            f"{line_num-1:4d} {sep} {content.rstrip()}"
                        )
                    except ValueError as err:
                        logger.error(
                            "Failed to parse line",
                            line=line,
                            error=err,
                            traceback=traceback.format_exc(),
                        )
                        continue

            return "\n".join(formatted_lines)
        except Exception as e:
            logger.error(
                "Failed to search file", error=e, traceback=traceback.format_exc()
            )
            return f"Failed to search file: {e}"

    def markdown(self, context: dict[str, Any] = {}):
        match self.action:
            case "search":
                return self._render_search_markdown()
            case "view":
                return self._render_view_markdown()
            case "create":
                return self._render_create_markdown()
            case "update":
                return self._render_update_markdown()
            case "insert":
                return self._render_insert_markdown()
            case "undo":
                return self._render_undo_markdown()
            case _:
                return self._render_error()

    def _render_error(self) -> str:
        return f"Error: {self.output}"

    def _render_search_markdown(self) -> str:
        template = Template(
            """
## ACI Results

action: `search`

search: `{{ output.content }}`

path: `{{ output.path }}`

{% if output.error %}
### Error
```
{{ output.error }}
```
{% else %}
### Output
```
{{ output.output }}
```
{% endif %}
"""
        )
        return template.render(output=self.output)

    def _render_view_markdown(self) -> str:
        template = Template(
            """
## ACI Results

action: `view`

path: `{{ output.path }}`

{% if output.line_start %}
line_start: `{{ output.line_start }}`
line_end: `{{ output.line_end }}`
{% endif %}

{% if output.error %}
### Error
```
{{ output.error }}
```
{% else %}
### Output
```
{{ output.output }}
```
{% endif %}
"""
        )
        return template.render(output=self.output)

    def _render_create_markdown(self) -> str:
        template = Template(
            """
## ACI Results

action: `create`

path: `{{ output.path }}`

{% if output.error %}
### Error
```
{{ output.error }}
```
{% else %}
### Output
```
{{ output.output }}
```
{% endif %}
"""
        )
        return template.render(output=self.output)

    def _render_insert_markdown(self) -> str:
        template = Template(
            """
## ACI Results

action: `insert`

path: `{{ output.path }}`

content: `{{ output.content }}`

line_number: `{{ output.insert_line_number }}`

{% if output.error %}
### Error
```
{{ output.error }}
```
{% else %}
### Output
```
{{ output.output }}
```
{% endif %}
"""
        )
        return template.render(output=self.output)

    def _render_undo_markdown(self) -> str:
        template = Template(
            """
## ACI Results

action: `undo`

path: `{{ output.path }}`

{% if output.error %}
### Error
```
{{ output.error }}
```
{% else %}
### Output
```
{{ output.output }}
```
{% endif %}
"""
        )
        return template.render(output=self.output)

    def _render_update_markdown(self) -> str:
        template = Template(
            """
## ACI Results

action: `update`

path: `{{ output.path }}`

old_content: `{{ old_content }}`

content: `{{ content }}`

{% if output.line_start %}
line_start: `{{ output.line_start }}`

line_end: `{{ output.line_end }}`
{% endif %}

{% if output.error %}
### Error
```
{{ output.error }}
```
{% else %}
### Output
```
{{ output.output }}
```
{% endif %}
"""
        )
        return template.render(
            output=self.output, old_content=self.old_content, content=self.content
        )


@dino(
    model="gpt-4o",
    response_model=ACITool,
)
async def coder(instruction: str):
    """
    You are a world class file system editor specialised in the `ACITool` tool.
    You will be given instructions to perform search, view, create, update,
    insert, and undo operations on files and directories.

    You will be returned the ACITool object to be executed.
    """
    return instruction
