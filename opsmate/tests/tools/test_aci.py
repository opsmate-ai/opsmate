import pytest
from opsmate.tools.aci import ACITool
from pathlib import Path


def test_aci_file_history_persistence():
    tool1 = ACITool(command="create", path="/tmp/test.txt", content="Hello, world!")
    tool1._file_history[Path("/tmp/test.txt")] = ["Hello, world!"]
    tool2 = ACITool(command="create", path="/tmp/test.txt", content="Hello, world!")
    assert tool2._file_history.get(Path("/tmp/test.txt")) == ["Hello, world!"]


@pytest.fixture
def test_file(tmp_path):
    file_path = tmp_path / "test.txt"
    yield str(file_path)
    if file_path.exists():
        file_path.unlink()


@pytest.mark.asyncio
async def test_file_create(tmp_path, test_file):
    tool = ACITool(command="create", path=test_file, content="Hello, world!")
    result = await tool.run()
    assert result.output == "File created successfully"
    assert tool.output.output == "File created successfully"
    assert tool._file_history[Path(test_file)] == ["Hello, world!"]

    # ensure that the file history is persisted in the class and updated
    test_file2 = str(tmp_path / "test2.txt")
    tool2 = ACITool(command="create", path=test_file2, content="Hello, world!")
    assert tool2._file_history[Path(test_file)] == ["Hello, world!"]

    # ensure duplicated file creation failed to init
    with pytest.raises(ValueError, match="test.txt already exists"):
        ACITool(command="create", path=test_file, content="Hello, world!")


@pytest.mark.asyncio
async def test_file_view(test_file):
    tool = ACITool(
        command="create",
        path=test_file,
        content="Hello, world!\nThis is cool.\nVery very cool",
    )
    result = await tool.run()
    assert result.output == "File created successfully"

    tool2 = ACITool(command="view", path=test_file)
    result2 = await tool2.run()
    assert (
        result2.output
        == """   0 | Hello, world!
   1 | This is cool.
   2 | Very very cool"""
    )

    tool3 = ACITool(command="view", path=test_file, line_range=(1, 2))
    result3 = await tool3.run()
    assert (
        result3.output
        == """   1 | This is cool.
   2 | Very very cool"""
    )

    # with pytest.raises(ValueError, match="end line number 3 is out of range"):
    tool = ACITool(command="view", path=test_file, line_range=(1, 3))
    result = await tool.run()
    assert (
        result.output
        == "Failed to view file: end line number 3 is out of range (file has 3 lines)"
    )


async def recover_file(file_path):
    tool = ACITool(command="undo", path=file_path)
    result = await tool.run()
    assert result.output == "Last file operation undone"


def assert_file_content(file_path, expected_content):
    with open(file_path, "r") as f:
        assert f.read() == expected_content


@pytest.mark.asyncio
async def test_file_insert(test_file):
    tool = ACITool(
        command="create",
        path=test_file,
        content="Hello, world!\nThis is cool.\nVery very cool",
    )
    result = await tool.run()
    assert result.output == "File created successfully"

    tool2 = ACITool(
        command="insert", path=test_file, content="Hello, world!", insert_line_number=1
    )
    result2 = await tool2.run()
    assert result2.output == "Content inserted successfully"

    assert_file_content(
        test_file, "Hello, world!\nHello, world!\nThis is cool.\nVery very cool"
    )

    await recover_file(test_file)

    assert_file_content(test_file, "Hello, world!\nThis is cool.\nVery very cool")

    # insert out of range
    tool3 = ACITool(
        command="insert", path=test_file, content="Hello, world!", insert_line_number=4
    )
    result3 = await tool3.run()
    assert (
        result3.output
        == "Failed to insert content into file: end line number 4 is out of range (file has 3 lines)"
    )
