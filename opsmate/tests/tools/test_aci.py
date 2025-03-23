import pytest
from opsmate.tools.aci import ACITool
from pathlib import Path
import tempfile
import shutil
from opsmate.tools.aci import coder, Result


def test_aci_file_history_persistence():
    tool1 = ACITool(action="create", path="/tmp/test.txt", content="Hello, world!")
    tool1._file_history[Path("/tmp/test.txt")] = ["Hello, world!"]
    tool2 = ACITool(action="create", path="/tmp/test.txt", content="Hello, world!")
    assert tool2._file_history.get(Path("/tmp/test.txt")) == ["Hello, world!"]


@pytest.fixture
def test_file(tmp_path):
    file_path = tmp_path / "test.txt"
    yield str(file_path)
    if file_path.exists():
        file_path.unlink()


@pytest.mark.asyncio
async def test_file_create(tmp_path, test_file):
    tool = ACITool(action="create", path=test_file, content="Hello, world!")
    result = await tool.run()
    assert result.output == "File created successfully"
    assert tool.output.output == "File created successfully"
    assert tool._file_history[Path(test_file)] == ["Hello, world!"]

    # ensure that the file history is persisted in the class and updated
    test_file2 = str(tmp_path / "test2.txt")
    tool2 = ACITool(action="create", path=test_file2, content="Hello, world!")
    assert tool2._file_history[Path(test_file)] == ["Hello, world!"]

    # ensure duplicated file creation failed to init
    with pytest.raises(ValueError, match="test.txt already exists"):
        ACITool(action="create", path=test_file, content="Hello, world!")


@pytest.mark.asyncio
async def test_file_view(test_file):
    tool = ACITool(
        action="create",
        path=test_file,
        content="Hello, world!\nThis is cool.\nVery very cool",
    )
    result = await tool.run()
    assert result.output == "File created successfully"

    tool2 = ACITool(action="view", path=test_file)
    result2 = await tool2.run()
    assert (
        result2.output
        == """   0 | Hello, world!
   1 | This is cool.
   2 | Very very cool"""
    )

    tool3 = ACITool(action="view", path=test_file, line_start=1, line_end=2)
    result3 = await tool3.run()
    assert (
        result3.output
        == """   1 | This is cool.
   2 | Very very cool"""
    )

    # with pytest.raises(ValueError, match="end line number 3 is out of range"):
    tool = ACITool(action="view", path=test_file, line_start=1, line_end=3)
    result = await tool.run()
    assert result == Result(
        error="Failed to view file: end line number 3 is out of range (file has 3 lines)",
        operation="view",
        path=test_file,
    )


@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_file_view_directory(temp_dir):
    # create subdirs
    (Path(temp_dir) / "subdir1").mkdir()
    (Path(temp_dir) / "subdir2").mkdir()
    (Path(temp_dir) / "subdir2" / "subdir3").mkdir()

    (Path(temp_dir) / "subdir1" / "file1.txt").touch()
    (Path(temp_dir) / "subdir1" / "file2.txt").touch()
    (Path(temp_dir) / "subdir2" / "file3.txt").touch()
    (Path(temp_dir) / "subdir2" / "subdir3" / "file4.txt").touch()

    tool = ACITool(action="view", path=str(temp_dir))
    result = await tool.run()
    assert (
        result.output
        == f"""{temp_dir}
{temp_dir}/subdir1
{temp_dir}/subdir1/file1.txt
{temp_dir}/subdir1/file2.txt
{temp_dir}/subdir2
{temp_dir}/subdir2/file3.txt
{temp_dir}/subdir2/subdir3
"""
    )


async def recover_file(file_path):
    tool = ACITool(action="undo", path=file_path)
    result = await tool.run()
    assert result == Result(
        output="File rolled back to previous state",
        operation="undo",
        path=file_path,
    )


def assert_file_content(file_path, expected_content):
    with open(file_path, "r") as f:
        assert f.read() == expected_content


@pytest.mark.asyncio
async def test_file_insert(test_file):
    tool = ACITool(
        action="create",
        path=test_file,
        content="Hello, world!\nThis is cool.\nVery very cool",
    )
    result = await tool.run()
    assert result.output == "File created successfully"

    tool2 = ACITool(
        action="insert", path=test_file, content="Hello, world!", insert_line_number=1
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
        action="insert", path=test_file, content="Hello, world!", insert_line_number=4
    )
    result3 = await tool3.run()
    assert result3 == Result(
        error="Failed to insert content into file: end line number 4 is out of range (file has 3 lines)",
        operation="insert",
        path=test_file,
        content="Hello, world!",
        insert_line_number=4,
    )


@pytest.mark.asyncio
async def test_file_update(test_file):
    tool = ACITool(
        action="create",
        path=test_file,
        content="Hello, world!\nThis is cool.\nVery very cool\nVery very cool",
    )
    result = await tool.run()
    assert result.output == "File created successfully"

    tool2 = ACITool(
        action="update",
        path=test_file,
        old_content="This is cool.",
        content="This is cold.",
    )
    result2 = await tool2.run()
    assert result2.output == "Content updated successfully"

    assert_file_content(
        test_file, "Hello, world!\nThis is cold.\nVery very cool\nVery very cool"
    )

    await recover_file(test_file)

    assert_file_content(
        test_file, "Hello, world!\nThis is cool.\nVery very cool\nVery very cool"
    )

    # update with empty content
    tool3 = ACITool(
        action="update", path=test_file, old_content="This is cool.\n", content=""
    )
    result3 = await tool3.run()
    assert result3.output == "Content updated successfully"

    assert_file_content(test_file, "Hello, world!\nVery very cool\nVery very cool")

    await recover_file(test_file)

    assert_file_content(
        test_file, "Hello, world!\nThis is cool.\nVery very cool\nVery very cool"
    )

    # update with non-existent content
    tool4 = ACITool(
        action="update",
        path=test_file,
        old_content="This is awesome.",
        content="This is hot.",
    )
    result4 = await tool4.run()
    assert result4 == Result(
        error="Old content not found in the specified line range",
        operation="update",
        path=test_file,
        old_content="This is awesome.",
        line_start=0,
        line_end=3,
    )

    # update with multiple occurrences of old content
    tool5 = ACITool(
        action="update",
        path=test_file,
        old_content="Very very cool",
        content="This is hot.",
    )
    result5 = await tool5.run()
    assert result5 == Result(
        error="Old content occurs more than once in the specified line range, please make sure its uniqueness",
        operation="update",
        path=test_file,
        old_content="Very very cool",
        line_start=0,
        line_end=3,
    )

    # update with line range
    tool6 = ACITool(
        action="update",
        path=test_file,
        old_content="Very very cool",
        content="This is hot.",
        line_start=0,
        line_end=2,
    )
    result6 = await tool6.run()
    assert result6.output == "Content updated successfully"

    assert_file_content(
        test_file, "Hello, world!\nThis is cool.\nThis is hot.\nVery very cool"
    )

    # update with empty old content
    tool7 = ACITool(
        action="update", path=test_file, old_content="", content="This is hot."
    )
    result7 = await tool7.run()
    assert result7.error == "Old content cannot be empty"


@pytest.mark.asyncio
async def test_file_search(test_file):
    tool = ACITool(
        action="create",
        path=test_file,
        content="this is cool\nvery very cool\nOK OK",
    )
    result = await tool.run()
    assert result.output == "File created successfully"

    tool2 = ACITool(action="search", path=test_file, content="this is cool")
    result2 = await tool2.run()
    # assert result2.output == "   0 | this is cool"
    assert (
        result2.output
        == """   0 | this is cool
   1 - very very cool
   2 - OK OK"""
    )

    tool3 = ACITool(action="search", path=test_file, content="cool")
    result3 = await tool3.run()
    assert result3.output == "   0 | this is cool\n   1 | very very cool\n   2 - OK OK"

    tool4 = ACITool(action="search", path=test_file, content="this is cool\nOK")
    result4 = await tool4.run()
    assert result4.output == "   0 | this is cool\n   1 - very very cool\n   2 | OK OK"


@pytest.mark.asyncio
async def test_file_search_directory(temp_dir):
    # create subdirs
    dir = Path(temp_dir) / "subdir1"
    dir.mkdir()
    dir = str(dir)

    file = Path(dir) / "file1.txt"
    file = str(file)

    tool = ACITool(action="create", path=file, content="this is cool")
    result = await tool.run()
    assert result.output == "File created successfully"

    tool2 = ACITool(action="search", path=dir, content="cool")
    result2 = await tool2.run()
    assert result2.output == f"{dir}/file1.txt\n---\n   0 | this is cool\n"


@pytest.mark.asyncio
async def test_coder(test_file):
    tool_call = await coder(f"what's in README.md")

    out = await tool_call.run()
    print(out.output)
