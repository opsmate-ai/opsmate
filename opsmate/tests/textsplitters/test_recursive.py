from opsmate.textsplitters.recursive import RecursiveTextSplitter
from opsmate.textsplitters.base import Chunk


def test_recursive_text_splitter():
    text = "Apple,banana,orange and tomato."
    splitter = RecursiveTextSplitter(
        chunk_size=7, chunk_overlap=3, separators=[".", ","]
    )
    output = splitter.split_text(text)
    expected_output = [
        Chunk(content="Apple", metadata={"seperator": ","}),
        Chunk(content="banana", metadata={"seperator": ","}),
        Chunk(content="orange and tomato", metadata={"seperator": ","}),
    ]
    assert output == expected_output

    text = "This is a piece of text."
    splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=5)
    output = splitter.split_text(text)
    expected_output = [
        Chunk(content="This is a", metadata={"seperator": " "}),
        Chunk(content="piece of text", metadata={"seperator": " "}),
        Chunk(content="text", metadata={"seperator": " "}),
    ]
    assert output == expected_output

    text = "This is a piece of text."
    splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=0)
    output = splitter.split_text(text)
    expected_output = [
        Chunk(content="This is a", metadata={"seperator": " "}),
        Chunk(content="piece of", metadata={"seperator": " "}),
        Chunk(content="text", metadata={"seperator": " "}),
    ]
    assert output == expected_output

    text = "This is a piece of text."
    splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=0, separators=[" "])
    output = splitter.split_text(text)
    expected_output = [
        Chunk(content="This is a", metadata={"seperator": " "}),
        Chunk(content="piece of", metadata={"seperator": " "}),
        Chunk(content="text.", metadata={"seperator": " "}),
    ]
    assert output == expected_output
