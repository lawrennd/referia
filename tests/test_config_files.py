"""CIP-0022 markdown config filenames and frontmatter load."""

from pathlib import Path

from referia.config.files import (
    config_filename,
    config_in_directory,
    is_explicit_config_path,
    iter_configs,
    read_config_mapping,
)


def test_markdown_wins_over_yml(tmp_path: Path):
    (tmp_path / "_referia.yml").write_text("title: yml\n", encoding="utf-8")
    (tmp_path / "_referia.md").write_text(
        "---\ntitle: md\n---\nBody with Data:\n- not yaml\n",
        encoding="utf-8",
    )
    found = config_in_directory(tmp_path)
    assert found is not None
    assert found.name == "_referia.md"
    assert config_filename(tmp_path) == "_referia.md"
    mapping = read_config_mapping(found)
    assert mapping["title"] == "md"


def test_yml_when_markdown_absent(tmp_path: Path):
    (tmp_path / "_referia.yml").write_text("title: yml\n", encoding="utf-8")
    assert config_filename(tmp_path) == "_referia.yml"
    assert config_in_directory(tmp_path).name == "_referia.yml"


def test_default_filename_when_empty_directory(tmp_path: Path):
    assert config_in_directory(tmp_path) is None
    assert config_filename(tmp_path) == "_referia.yml"


def test_explicit_config_path_suffixes():
    assert is_explicit_config_path("01_turns.md")
    assert is_explicit_config_path("/a/_referia.yml")
    assert is_explicit_config_path("notes.yaml")
    assert not is_explicit_config_path("01_turns/")
    assert not is_explicit_config_path("")


def test_read_config_mapping_empty_and_non_mapping(tmp_path: Path):
    empty = tmp_path / "empty.md"
    empty.write_text("   \n", encoding="utf-8")
    assert read_config_mapping(empty) == {}
    listed = tmp_path / "list.yml"
    listed.write_text("- a\n- b\n", encoding="utf-8")
    assert read_config_mapping(listed) == {}


def test_frontmatter_crlf_and_missing_close(tmp_path: Path):
    crlf = tmp_path / "win.md"
    crlf.write_text("---\r\ntitle: win\r\n---\r\nbody\r\n", encoding="utf-8")
    assert read_config_mapping(crlf)["title"] == "win"
    open_fm = tmp_path / "open.md"
    open_fm.write_text("---\ntitle: still\n", encoding="utf-8")
    assert read_config_mapping(open_fm)["title"] == "still"
    no_fm = tmp_path / "plain.md"
    no_fm.write_text("just markdown\n", encoding="utf-8")
    assert read_config_mapping(no_fm) == {}


def test_iter_configs_prefers_markdown_in_each_directory(tmp_path: Path):
    nested = tmp_path / "stage"
    nested.mkdir()
    (tmp_path / "_referia.yml").write_text("title: root yml\n", encoding="utf-8")
    (tmp_path / "_referia.md").write_text("---\ntitle: root md\n---\n", encoding="utf-8")
    (nested / "_referia.yml").write_text("title: nested\n", encoding="utf-8")
    names = [p.relative_to(tmp_path).as_posix() for p in iter_configs(tmp_path)]
    assert names == ["_referia.md", "stage/_referia.yml"]
