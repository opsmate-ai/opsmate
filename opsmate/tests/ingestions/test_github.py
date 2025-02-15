import pytest
import httpx
from unittest.mock import AsyncMock, Mock
from opsmate.ingestions.github import GithubIngestion
import os
import base64


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def github_ingestion(mock_client):
    return GithubIngestion(
        repo="owner/repo",
        github_token="fake-token",
        branch="main",
        client=mock_client,
    )


@pytest.mark.asyncio
async def test_validate_github_token():
    # Test with direct token
    ingestion = GithubIngestion(repo="owner/repo", github_token="test-token")
    assert ingestion.github_token == "test-token"

    # Test with environment variable
    old_token = os.getenv("GITHUB_TOKEN")
    os.environ["GITHUB_TOKEN"] = "env-token"
    ingestion = GithubIngestion(repo="owner/repo", github_token="")
    assert ingestion.github_token == "env-token"
    if old_token:
        os.environ["GITHUB_TOKEN"] = old_token
    else:
        del os.environ["GITHUB_TOKEN"]

    # Test with missing token
    old_token = os.getenv("GITHUB_TOKEN")
    if old_token:
        del os.environ["GITHUB_TOKEN"]
    with pytest.raises(ValueError, match="GitHub token is required"):
        GithubIngestion(repo="owner/repo")
    if old_token:
        os.environ["GITHUB_TOKEN"] = old_token


@pytest.mark.asyncio
async def test_get_files(github_ingestion, mock_client):
    mock_response = Mock(spec=httpx.Response)
    mock_response.json.return_value = {
        "tree": [
            {"type": "blob", "path": "file1.txt"},
            {"type": "tree", "path": "dir"},
            {"type": "blob", "path": "file2.py"},
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response

    files = []
    async with mock_client as client:
        async for file in github_ingestion.get_files():
            files.append(file)

    assert files == ["file1.txt", "file2.py"]
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_files_with_glob(github_ingestion, mock_client):
    github_ingestion.glob = "*.py"
    mock_response = Mock(spec=httpx.Response)
    mock_response.json.return_value = {
        "tree": [
            {"type": "blob", "path": "file1.txt"},
            {"type": "tree", "path": "dir"},
            {"type": "blob", "path": "file2.py"},
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response

    files = []
    async with mock_client as client:
        async for file in github_ingestion.get_files():
            files.append(file)

    assert files == ["file2.py"]


@pytest.mark.asyncio
async def test_get_file_with_metadata(github_ingestion, mock_client):
    content = "Hello, World!"
    encoded_content = base64.b64encode(content.encode()).decode()

    mock_response = Mock(spec=httpx.Response)
    mock_response.json.return_value = {
        "content": encoded_content,
        "html_url": "https://github.com/owner/repo/blob/main/test.txt",
        "sha": "1234567890",
    }
    mock_response.raise_for_status.return_value = None

    github_ingestion.client = mock_client
    mock_client.get.return_value = mock_response

    result = await github_ingestion.get_file_with_metadata("test.txt")
    assert result.get("content") == content
    assert result.get("sha") == "1234567890"
    assert result.get("html_url") == "https://github.com/owner/repo/blob/main/test.txt"


@pytest.mark.asyncio
async def test_load(github_ingestion):
    # Mock get_files
    tree_query_response = Mock(spec=httpx.Response)
    tree_query_response.json.return_value = {
        "tree": [
            {"type": "blob", "path": "file1.txt"},
            {"type": "tree", "path": "dir"},
            {"type": "blob", "path": "file2.py"},
        ]
    }
    tree_query_response.raise_for_status.return_value = None

    file_1_content_response = Mock(spec=httpx.Response)
    file_1_content_response.json.return_value = {
        "content": base64.b64encode("content1".encode()).decode(),
        "html_url": "https://github.com/owner/repo/blob/main/file1.txt",
        "sha": "1234567890",
    }
    file_1_content_response.raise_for_status.return_value = None

    file_2_content_response = Mock(spec=httpx.Response)
    file_2_content_response.json.return_value = {
        "content": base64.b64encode("content2".encode()).decode(),
        "html_url": "https://github.com/owner/repo/blob/main/file2.py",
        "sha": "1234567890",
    }
    file_2_content_response.raise_for_status.return_value = None

    def side_effect(url: str, headers: dict):
        if "tree" in url:
            return tree_query_response
        elif "file1.txt" in url:
            return file_1_content_response
        elif "file2.py" in url:
            return file_2_content_response
        else:
            raise Exception("Invalid URL")

    github_ingestion.client.get.side_effect = side_effect

    documents = []
    async for doc in github_ingestion.load():
        documents.append(doc)

    assert len(documents) == 2
    assert documents[0].content == "content1"
    assert documents[0].metadata == {
        "path": "file1.txt",
        "repo": "owner/repo",
        "branch": "main",
        "source": "https://github.com/owner/repo/blob/main/file1.txt",
        "sha": "1234567890",
    }
    assert documents[1].data_provider == "github"
    assert documents[1].data_source == "owner/repo"

    assert documents[1].content == "content2"
    assert documents[1].metadata == {
        "path": "file2.py",
        "repo": "owner/repo",
        "branch": "main",
        "source": "https://github.com/owner/repo/blob/main/file2.py",
        "sha": "1234567890",
    }
    assert documents[1].data_provider == "github"
    assert documents[1].data_source == "owner/repo"


@pytest.mark.skipif(os.getenv("GITHUB_TOKEN") is None, reason="GITHUB_TOKEN is not set")
@pytest.mark.asyncio
async def test_integration():
    github_ingestion = GithubIngestion(
        repo="jingkaihe/hjktech-metal",
        github_token=os.getenv("GITHUB_TOKEN"),
        branch="main",
        glob="**/*.md",
    )

    try:
        docs = [doc async for doc in github_ingestion.load()]
        assert len(docs) == 1
        assert docs[0].metadata["path"] == "README.md"
        assert docs[0].metadata["repo"] == "jingkaihe/hjktech-metal"
        assert docs[0].metadata["branch"] == "main"
        assert docs[0].data_provider == "github"
        assert docs[0].data_source == "jingkaihe/hjktech-metal"
    except Exception as e:
        assert False, f"Should not raise error but got: {e}"


def test_from_config():
    old_token = os.getenv("GITHUB_TOKEN")
    os.environ["GITHUB_TOKEN"] = "env-token"

    config = {
        "opsmate/opsmate:main": "*.md",
        "opsmate/opsmate2": "*.txt",
        "opsmate/opsmate3:dev": "*.txt",
    }
    ingestions = GithubIngestion.from_configmap(config)
    assert len(ingestions) == 3
    assert ingestions[0].repo == "opsmate/opsmate"
    assert ingestions[0].branch == "main"
    assert ingestions[0].glob == "*.md"
    assert ingestions[1].repo == "opsmate/opsmate2"
    assert ingestions[1].branch == "main"
    assert ingestions[1].glob == "*.txt"
    assert ingestions[2].repo == "opsmate/opsmate3"
    assert ingestions[2].branch == "dev"
    assert ingestions[2].glob == "*.txt"

    if old_token:
        os.environ["GITHUB_TOKEN"] = old_token
    else:
        del os.environ["GITHUB_TOKEN"]
