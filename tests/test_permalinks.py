"""CIP-0022 permalink-tree URL mode."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from referia.config.permalinks import (
    PermalinkCollisionError,
    build_permalink_tree,
    is_permalink_config,
    normalize_permalink,
    resolve_url_mode,
)
from referia.web.app import create_app


def _page(path: Path, permalink: str, title: str = "Stage") -> None:
    path.write_text(
        "---\n"
        "layout: referia\n"
        f"permalink: {permalink}\n"
        "referia_config_version: 2\n"
        f"title: {title}\n"
        "---\n\nBody\n"
    )


def test_normalize_permalink_trailing_slash():
    assert normalize_permalink("/01_turns") == "/01_turns/"
    assert normalize_permalink("/01_turns/") == "/01_turns/"
    assert normalize_permalink("01_turns") == "/01_turns/"
    assert normalize_permalink("/") == "/"
    assert normalize_permalink("") == "/"


def test_layout_referia_without_version_is_not_a_config():
    assert not is_permalink_config({"layout": "referia", "permalink": "/x/"})
    assert is_permalink_config(
        {
            "layout": "referia",
            "permalink": "/x/",
            "referia_config_version": 2,
        }
    )


def test_build_tree_maps_top_level_filenames(tmp_path):
    _page(tmp_path / "index.md", "/", "Hub")
    _page(tmp_path / "01_turns.md", "/01_turns/", "Turns")
    tree = build_permalink_tree(tmp_path)
    assert set(tree) == {"/", "/01_turns/"}
    assert tree["/01_turns/"].path == tmp_path / "01_turns.md"
    assert tree["/01_turns/"].directory == tmp_path
    assert tree["/"].path.name == "index.md"


def test_duplicate_permalink_raises(tmp_path):
    _page(tmp_path / "a.md", "/01_turns/")
    _page(tmp_path / "b.md", "/01_turns/")
    with pytest.raises(PermalinkCollisionError) as exc:
        build_permalink_tree(tmp_path)
    assert exc.value.permalink == "/01_turns/"


def test_exclude_honoured(tmp_path):
    _page(tmp_path / "01_turns.md", "/01_turns/")
    hidden = tmp_path / "drafts"
    hidden.mkdir()
    _page(hidden / "skip.md", "/skip/")
    tree = build_permalink_tree(tmp_path, exclude=["drafts"])
    assert "/skip/" not in tree
    assert "/01_turns/" in tree


def test_readme_without_layout_is_not_in_tree(tmp_path):
    (tmp_path / "README.md").write_text("# Study\n")
    _page(tmp_path / "01_chunk.md", "/01_chunk/")
    tree = build_permalink_tree(tmp_path)
    assert set(tree) == {"/01_chunk/"}


def test_resolve_url_mode_defaults_path(tmp_path):
    assert resolve_url_mode(tmp_path) == "path"
    (tmp_path / "_config.yml").write_text("referia:\n  urls: permalink\n")
    assert resolve_url_mode(tmp_path) == "permalink"
    assert resolve_url_mode(tmp_path, "path") == "path"


def test_cli_override_permalink_serves_top_level_md(tmp_path):
    _page(tmp_path / "01_turns.md", "/01_turns/", "Turns")
    (tmp_path / "_referia.yml").write_text("title: leftover path file\n")
    mock = MagicMock()
    mock.index_list.return_value = ["row"]
    mock.get_index.return_value = "row"
    mock.get_viewer_specs.return_value = []
    mock.get_review_specs.return_value = []
    mock.get_widget_specs.return_value = []
    mock.render_viewer_html.return_value = ""
    mock.get_value.return_value = ""
    mock.get_row_data.return_value = {}
    with patch("referia.assess.web_review.WebReviewer", return_value=mock):
        app = create_app(root=str(tmp_path), urls="permalink")
        with TestClient(app) as client:
            resp = client.get("/01_turns/")
            missing = client.get("/01_turns/referia.md")
            leftover = client.get("/01_turns/_referia.yml")
    assert resp.status_code == 200
    assert missing.status_code == 404
    assert leftover.status_code == 404
    mock.index_list.assert_called()


def test_default_path_mode_still_uses_directory_yml(tmp_path):
    stage = tmp_path / "reviews" / "intro"
    stage.mkdir(parents=True)
    (stage / "_referia.yml").write_text("title: path tree\n")
    mock = MagicMock()
    mock.index_list.return_value = ["row"]
    mock.get_index.return_value = "row"
    mock.get_viewer_specs.return_value = []
    mock.get_review_specs.return_value = []
    mock.get_widget_specs.return_value = []
    mock.render_viewer_html.return_value = ""
    mock.get_value.return_value = ""
    mock.get_row_data.return_value = {}
    with patch("referia.assess.web_review.WebReviewer", return_value=mock):
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/reviews/intro/")
    assert resp.status_code == 200
    assert app.state.url_mode == "path"
    assert app.state.permalink_tree is None
