from opsmate.dino.types import ToolCall
from pydantic import BaseModel, Field, model_validator
from typing import Tuple, Dict, List, Optional, ClassVar, Self
from collections import defaultdict
from pathlib import Path
from opsmate.tools.utils import maybe_truncate_text
from opsmate.dino import dino
import asyncio
import os
import structlog

logger = structlog.get_logger(__name__)


class Result(BaseModel):
    """
    Result is a model that represents the result of a tool call.
    """

    output: str


class ACITool(ToolCall):
    """
    # ACITool

    File system utility with the following commands:

    search <file|dir> <content>           # Search in file/directory
    view <file|dir> [start] [end]        # View file (optional line range) or directory
    create <file> <content>          # Create new file
    update <file> <old> <new>        # Replace content (old must be unique)
    append <file> <line> <content>   # Insert at line number
    undo <file>                      # Undo last file change

    Notes:
    - Line numbers are 0-indexed
    - Directory view: 2-depth, ignores dotfiles
    - Empty new content in update deletes old content
    """

    _file_history: ClassVar[Dict[Path, List[str]]] = defaultdict(list)

    output: Result = Field(
        description="The result of the file operation, DO NOT POPULATE THIS FIELD",
        default=None,
    )

    command: str = Field(
        description="The command to execute",
        choices=["search", "view", "create", "update", "insert", "undo"],
    )

    path: str = Field(description="The path of the file or directory to be operated on")

    insert_line_number: Optional[int] = Field(
        description="The line number to insert the content at, only applicable for the `insert` command. Note the line number is 0-indexed.",
        default=None,
    )

    line_start: Optional[int] = Field(
        description="The start line number to be operated on, only applicable for the 'view' command. Note the line number is 0-indexed.",
        default=None,
    )
    line_end: Optional[int] = Field(
        description="The end line number to be operated on, only applicable for the 'view' command. Note the line number is 0-indexed.",
        default=None,
    )

    content: Optional[str] = Field(
        description="The content to be added to the file, only applicable for the `search`, `create`, `update` and `insert` commands.",
        default=None,
    )

    old_content: Optional[str] = Field(
        description="The old content to be replaced by the new content, only applicable for the `update` command.",
        default=None,
    )

    @model_validator(mode="after")
    def validate_path(self) -> Self:
        if self.command != "create":
            if not Path(self.path).exists():
                raise ValueError(f"File or directory {self.path} does not exist")
        else:
            if Path(self.path).exists():
                raise ValueError(f"File or directory {self.path} already exists")
        return self

    @model_validator(mode="after")
    def validate_search_command(self) -> Self:
        if self.command == "search":
            if self.content is None:
                self.content = ""
        return self

    @model_validator(mode="after")
    def validate_view_command(self) -> Self:
        if self.command == "view":
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
    def validate_create_command(self) -> Self:
        if self.command == "create":
            if self.content is None:
                raise ValueError("content is required for the create command")
        return self

    @model_validator(mode="after")
    def validate_update_command(self) -> Self:
        if self.command == "update":
            if self.old_content is None:
                raise ValueError("old_content is required for the update command")
            if self.content is None:
                raise ValueError("new_content is required for the update command")
        return self

    @model_validator(mode="after")
    def validate_insert_command(self) -> Self:
        if self.command == "insert":
            if self.content is None:
                raise ValueError("content is required for the insert command")
            if self.insert_line_number is None:
                raise ValueError(
                    "insert_line_number is required for the insert command"
                )
        return self

    @model_validator(mode="after")
    def validate_undo_command(self) -> Self:
        if self.command == "undo":
            if self.path is None:
                raise ValueError("path is required for the undo command")
        return self

    async def __call__(self) -> Result:
        logger.info(
            "executing command",
            command=self.command,
            path=self.path,
            content=self.content,
            old_content=self.old_content,
            insert_line_number=self.insert_line_number,
            line_start=self.line_start,
            line_end=self.line_end,
        )
        if self.command == "search":
            return await self.search()
        elif self.command == "view":
            return await self.view()
        elif self.command == "create":
            return await self.create()
        elif self.command == "update":
            return await self.update()
        elif self.command == "insert":
            return await self.insert()
        elif self.command == "undo":
            return await self.undo()
        else:
            raise ValueError(f"Invalid command: {self.command}")

    async def create(self) -> Result:
        try:
            Path(self.path).write_text(self.content)
            self._file_history[Path(self.path)].append(self.content)
        except Exception as e:
            return Result(output=f"Failed to create file: {e}")
        return Result(output="File created successfully")

    async def view(self) -> Result:
        if Path(self.path).is_file():
            return await self._view_file()
        elif Path(self.path).is_dir():
            return await self._view_directory()
        else:
            return Result(output=f"Invalid path: {self.path}")

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

            return Result(output=maybe_truncate_text(numbered_contents))
        except Exception as e:
            return Result(output=f"Failed to view file: {e}")

    async def _view_directory(self) -> Result:
        try:
            process = await asyncio.create_subprocess_shell(
                rf"find {self.path} -maxdepth 2 -not -path '*/\.*' -not -name '.*' | sort",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            # Add 5 second timeout to communicate
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
            return Result(output=maybe_truncate_text(stdout.decode()))
        except asyncio.TimeoutError:
            # Kill the process if it times out
            process.kill()
            return Result(output="Directory listing timed out after 5 seconds")
        except Exception as e:
            return Result(output=f"Failed to view directory: {e}")

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

            return Result(output="Content inserted successfully")
        except Exception as e:
            return Result(output=f"Failed to insert content into file: {e}")

    async def update(self) -> Result:
        """
        Replace the old content with the new content.
        """
        path = Path(self.path)
        file_content = path.read_text()

        occurrences = file_content.count(self.old_content)
        if occurrences == 0:
            return Result(output="Old content not found in file")
        elif occurrences > 1:
            return Result(
                output="Old content occurs more than once in file, please make sure its uniqueness"
            )
        file_content = file_content.replace(self.old_content, self.content)
        path.write_text(file_content)
        self._file_history[path].append(file_content)
        return Result(output="Content updated successfully")

    async def undo(self) -> Result:
        """
        Undo the last file operation.
        """
        path = Path(self.path)
        if len(self._file_history[path]) <= 1:
            return Result(output="There is no history of file operations")
        self._file_history[path].pop()
        latest_content = self._file_history[path][-1]
        path.write_text(latest_content)
        return Result(output="Last file operation undone")

    async def search(self) -> Result:
        """
        Search for a pattern in a file or directory using regex.
        """
        path = Path(self.path)
        try:
            if path.is_file():
                result = await self._search_file(path)
                return Result(output=maybe_truncate_text(result))

            elif path.is_dir():
                results = ""
                for root, _dirs, files in os.walk(path):
                    for file in files:
                        if file.startswith(".") or root.startswith("."):
                            continue
                        result = await self._search_file(os.path.join(root, file))
                        if result:
                            results += f"{root}/{file}\n---\n{result}\n"
                logger.info("search results", results=results)
                return Result(output=maybe_truncate_text(results))

            else:
                return Result(output=f"Invalid path: {path}")

        except asyncio.TimeoutError:
            return Result(output="Search timed out after 5 seconds")
        except Exception as e:
            return Result(output=f"Failed to search: {e}")

    async def _search_file(self, filename: str) -> str:
        try:
            cmd = f"grep -En '{self.content}' {filename}"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
            result = stdout.decode().strip()

            if not result:
                return "Pattern not found"

            formatted_lines = []
            for line in result.splitlines():
                line_num, content = line.split(":", 1)
                formatted_lines.append(f"{int(line_num)-1:4d} | {content.rstrip()}")

            return "\n".join(formatted_lines)
        except Exception as e:
            return f"Failed to search file: {e}"


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
