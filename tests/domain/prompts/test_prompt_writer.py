import pytest

from claudit.domain.prompts import PromptWriter


def test_prompt_writer_writes_content(tmp_path):
    writer = PromptWriter(tmp_path, filename="output.md")

    path = writer.write("hello world")

    assert path.exists()
    assert path.read_text(encoding="utf-8") == "hello world"


def test_prompt_writer_allows_filename_override(tmp_path):
    writer = PromptWriter(tmp_path, filename="default.md")

    path = writer.write("content", filename="custom.md")

    assert path.name == "custom.md"
    assert path.read_text(encoding="utf-8") == "content"


def test_prompt_writer_requires_filename(tmp_path):
    writer = PromptWriter(tmp_path)

    with pytest.raises(ValueError, match="requires a filename"):
        writer.write("content")
