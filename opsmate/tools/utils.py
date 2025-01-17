import tempfile


def maybe_truncate_text(text: str, max_length: int = 10000) -> str:
    tmp_file = _write_text_to_tmp_file(text)

    truncate_notice = f"""<truncated>
The initial content is truncated due to the maximum text length reached
Please refer to the file for the full content: {tmp_file}
<truncated>
"""
    if len(text) > max_length:
        return truncate_notice + text[len(text) - max_length :]
    return text


def _write_text_to_tmp_file(text: str) -> str:
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    tmp_file.write(text.encode())
    tmp_file.close()
    return tmp_file.name
