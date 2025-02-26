import pytest
from opsmate.tools.system import (
    HttpGet,
    HttpCall,
    HtmlToText,
    FileRead,
    FileWrite,
    FileAppend,
    FilesList,
    FilesFind,
    FileDelete,
    SysStats,
    SysEnv,
    HttpResponse,
)
import os
import json
import respx
import tempfile
import shutil
from httpx import Response


# Fixtures
@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_file(temp_dir):
    file_path = os.path.join(temp_dir, "test.txt")
    with open(file_path, "w") as f:
        f.write("test content")
    yield file_path
    os.remove(file_path)


# HTTP Tests
@pytest.mark.asyncio
@respx.mock
async def test_http_get():
    respx.get("https://example.com").mock(
        return_value=Response(200, text="Hello World")
    )
    http_get = HttpGet(url="https://example.com")
    result = await http_get.run()
    assert result.text == "Hello World"
    assert result.status_code == 200


@pytest.mark.asyncio
@respx.mock
async def test_http_get_failure():
    respx.get("https://example.com").mock(return_value=Response(404, text="No"))
    http_get = HttpGet(url="https://example.com")
    result = await http_get.run()
    assert result.text == "No"
    assert result.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_http_call():
    test_data = {"key": "value"}
    respx.post("https://example.com").mock(return_value=Response(200, text="Yes"))
    http_call = HttpCall(
        url="https://example.com", data=json.dumps(test_data), method="POST"
    )
    result = await http_call.run()
    assert result.text == "Yes"
    assert result.status_code == 200


@pytest.mark.asyncio
@respx.mock
async def test_http_call_failure():
    test_data = {"key": "value"}
    respx.post("https://example.com").mock(return_value=Response(500, text="No"))
    http_call = HttpCall(
        url="https://example.com", data=json.dumps(test_data), method="POST"
    )
    result = await http_call.run()
    assert result.text == "No"
    assert result.status_code == 500


@pytest.mark.asyncio
@respx.mock
async def test_http_to_text():
    respx.get("https://example.com").mock(
        return_value=Response(200, text="<h1>Hello World</h1>")
    )
    http_text = HtmlToText(url="https://example.com")
    result = await http_text()
    assert "Hello World" in result.text
    assert result.status_code == 200


@pytest.mark.asyncio
@respx.mock
async def test_http_to_text_failure():
    respx.get("https://example.com").mock(
        return_value=Response(404, text="<h1>No</h1>")
    )
    http_text = HtmlToText(url="https://example.com")
    result = await http_text.run()
    assert "No" in result.text
    assert result.status_code == 404


# File Operation Tests
@pytest.mark.asyncio
async def test_file_read(sample_file):
    file_read = FileRead(path=sample_file)
    result = await file_read.run()
    assert result == "test content"


@pytest.mark.asyncio
async def test_file_write(temp_dir):
    test_path = os.path.join(temp_dir, "write_test.txt")
    file_write = FileWrite(path=test_path, data="new content")
    await file_write.run()

    with open(test_path, "r") as f:
        content = f.read()
    assert content == "new content"


@pytest.mark.asyncio
async def test_file_append(sample_file):
    file_append = FileAppend(path=sample_file, data="\nappended content")
    await file_append.run()

    with open(sample_file, "r") as f:
        content = f.read()
    assert content == "test content\nappended content"


@pytest.mark.asyncio
async def test_list_files(temp_dir):
    # Create some test files
    os.makedirs(os.path.join(temp_dir, "subdir"))
    open(os.path.join(temp_dir, "file1.txt"), "w").close()
    open(os.path.join(temp_dir, "subdir/file2.txt"), "w").close()

    list_files = FilesList(path=temp_dir)
    result = await list_files.run()
    assert "file1.txt" in result
    assert "subdir/file2.txt" in result

    os.remove(os.path.join(temp_dir, "file1.txt"))
    os.remove(os.path.join(temp_dir, "subdir/file2.txt"))
    os.rmdir(os.path.join(temp_dir, "subdir"))


@pytest.mark.asyncio
async def test_find_files(temp_dir):
    # Create test files
    test_file = "findme.txt"
    open(os.path.join(temp_dir, test_file), "w").close()

    find_files = FilesFind(path=temp_dir, filename=test_file)
    result = await find_files.run()
    assert test_file in result


@pytest.mark.asyncio
async def test_file_delete(temp_dir):
    test_path = os.path.join(temp_dir, "delete_test.txt")
    open(test_path, "w").close()

    file_delete = FileDelete(path=test_path)
    await file_delete.run()
    assert not os.path.exists(test_path)


@pytest.mark.asyncio
async def test_sys_stats(sample_file):
    sys_stats = SysStats(path=sample_file)
    result = await sys_stats.run()
    assert "st_size" in result


@pytest.mark.asyncio
async def test_sys_env():
    os.environ["TEST_VAR"] = "test_value"
    sys_env = SysEnv(env_vars=["TEST_VAR"])
    result = await sys_env()
    assert "TEST_VAR: test_value" in result

    del os.environ["TEST_VAR"]
