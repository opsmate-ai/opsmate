from opsmate.textsplitters.recursive import RecursiveTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter


def test_recursive_text_splitter():
    text = "Apple,banana,orange and tomato."
    splitter = RecursiveTextSplitter(
        chunk_size=7, chunk_overlap=3, separators=[".", ","]
    )
    output = splitter.split_text(text)
    expected_output = ["Apple", "banana", "orange and tomato"]
    assert output == expected_output

    text = "This is a piece of text."
    splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=5)
    output = splitter.split_text(text)
    expected_output = ["This is a", "piece of text.", "text."]
    assert output == expected_output

    text = "This is a piece of text."
    splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=0)
    output = splitter.split_text(text)
    expected_output = ["This is a", "piece of", "text."]
    assert output == expected_output
