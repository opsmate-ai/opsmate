from opsmate.dino.types import ToolCall
from pydantic import BaseModel, Field, model_validator
from typing import Tuple, Dict, List, Optional, ClassVar, Self
from collections import defaultdict
from pathlib import Path


class Result(BaseModel):
    """
    Result is a model that represents the result of a tool call.
    """

    output: str


class ACITool(ToolCall):
    """
    ACITool is a tool that specialised in searching, viewing, creating, appending, and updating files
    in the operating system file system.

    Here are a list of valid operations:

    ## Search

    To search for a pattern in a file, use the following command:

    search <file_path> <content>

    To search for a pattern in a directory, use the following command:

    search <directory_path> <content>

    ## View

    To view the contents of a file, use the following command:

    view <file_path>

    To view the contents of a file with 0-indexed line range, use the following command:

    view <file_path> <start_line> <end_line>

    ## Create

    To create a file, use the following command:

    create <file_path> <content>

    ## Update

    To update a file, use the following command. Note:

    * when the new content is an empty string, the old content will be removed.
    * The old content must occur only once in the file to ensure uniqueness.

    update <file_path> <old_content> <new_content>


    ## Insert

    To insert content into a file, use the following command. Note that the line number is 0-indexed.

    append <file_path> <line_number> <content>


    ## Undo

    To undo the last file operation, use the following command:

    undo <file_path>
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

    line_range: Optional[Tuple[int, int]] = Field(
        description="The line number range to be operated on, only applicable for the 'view' command. Note the line number is 0-indexed.",
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
            if self.line_range:
                if len(self.line_range) != 2:
                    raise ValueError("line_range must be a tuple of two integers")
                start, end = self.line_range
                if start < 0:
                    raise ValueError("start line number cannot be negative")
                if end < start:
                    raise ValueError(
                        "end line number must be greater than or equal to start line number"
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
        """
        Return the contents with line numbers of the file.
        """
        try:
            with open(self.path, "r") as f:
                lines = f.readlines()

            # Handle line range if specified
            if self.line_range:
                start, end = self.line_range
                if end >= len(lines):
                    raise ValueError(
                        f"end line number {end} is out of range (file has {len(lines)} lines)"
                    )
                lines = lines[start : end + 1]

            # Format lines with line numbers (0-indexed)
            numbered_contents = ""
            for i, line in enumerate(lines):
                line_number = i if not self.line_range else i + self.line_range[0]
                numbered_contents += f"{line_number:4d} | {line}"

            return Result(output=numbered_contents)
        except Exception as e:
            return Result(output=f"Failed to view file: {e}")

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
