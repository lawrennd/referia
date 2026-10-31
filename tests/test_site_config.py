"""Jekyll-style ``_config.yml`` → GitHub edit constants."""

from pathlib import Path

from referia.config.site import (
    find_site_config,
    flatten_site_config,
    github_edit_url,
    load_site_constants,
)


def test_flatten_ghub_uses_organization_and_defaults_branch():
    site = flatten_site_config(
        {
            "title": "Study",
            "ghub": {
                "edit": True,
                "organization": "mlatcl",
                "repository": "dods-ai-dialogue",
            },
        }
    )
    assert site["ghub_organization"] == "mlatcl"
    assert site["ghub_repository"] == "dods-ai-dialogue"
    assert site["ghub_branch"] == "main"
    assert site["ghub_edit"] is True
    assert site["site_title"] == "Study"
    assert site["referia_urls"] == "path"


def test_flatten_splits_org_slash_repo_and_github_username():
    site = flatten_site_config(
        {
            "github_username": "mlatcl",
            "ghub": {"repository": "mlatcl/dods-ai-dialogue", "branch": "gh-pages"},
        }
    )
    assert site["ghub_organization"] == "mlatcl"
    assert site["ghub_repository"] == "dods-ai-dialogue"
    assert site["ghub_branch"] == "gh-pages"


def test_github_edit_url_joins_directory_and_relpath():
    site = {
        "ghub_edit": True,
        "ghub_organization": "mlatcl",
        "ghub_repository": "dods-ai-dialogue",
        "ghub_branch": "main",
        "ghub_directory": "",
    }
    assert (
        github_edit_url(site, "01_turns/_referia.md")
        == "https://github.com/mlatcl/dods-ai-dialogue/edit/main/01_turns/_referia.md"
    )
    site["ghub_directory"] = "studies/ai"
    assert github_edit_url(site, "01_turns/_referia.md").endswith(
        "studies/ai/01_turns/_referia.md"
    )


def test_github_edit_url_none_when_edit_false_or_incomplete():
    assert github_edit_url({"ghub_edit": False, "ghub_organization": "a",
                            "ghub_repository": "b", "ghub_branch": "main"},
                           "x.md") is None
    assert github_edit_url({"ghub_edit": True, "ghub_organization": "",
                            "ghub_repository": "b", "ghub_branch": "main"},
                           "x.md") is None


def test_load_site_constants_from_serve_root(tmp_path: Path):
    (tmp_path / "_config.yml").write_text(
        "github_username: mlatcl\n"
        "ghub:\n"
        "  edit: true\n"
        "  repository: dods-ai-dialogue\n"
        "  branch: main\n",
        encoding="utf-8",
    )
    stage = tmp_path / "01_turns"
    stage.mkdir()
    config = stage / "_referia.md"
    config.write_text("---\ntitle: turns\n---\n", encoding="utf-8")
    site = load_site_constants(stage, config_path=config, stop=tmp_path)
    assert (
        site["github_edit_url"]
        == "https://github.com/mlatcl/dods-ai-dialogue/edit/main/01_turns/_referia.md"
    )
    assert find_site_config(stage, stop=tmp_path) == tmp_path / "_config.yml"


def test_load_site_constants_empty_without_config(tmp_path: Path):
    stage = tmp_path / "01_turns"
    stage.mkdir()
    assert load_site_constants(stage, config_path=stage / "_referia.md") == {}


def test_referia_url_mode_invalid_and_ghub_list():
    from referia.config.site import referia_url_mode

    assert referia_url_mode({"referia": ["not-a-map"]}) == "path"
    assert referia_url_mode({"referia": {"urls": "tree"}}) == "path"
    assert referia_url_mode({"referia": {"urls": "permalink"}}) == "permalink"
    site = flatten_site_config(
        {"ghub": [{"edit": True, "organization": "o", "repository": "r"}]}
    )
    assert site["ghub_organization"] == "o"
    assert github_edit_url(site, "") is None


def test_find_site_config_stops_at_git_and_reads_file_start(tmp_path: Path):
    repo = tmp_path / "repo"
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    (repo / ".git").mkdir()
    (tmp_path / "_config.yml").write_text("title: above repo\n")
    assert find_site_config(nested) is None
    cfg = tmp_path / "study" / "_config.yml"
    cfg.parent.mkdir()
    cfg.write_text("title: from file\n", encoding="utf-8")
    assert find_site_config(cfg) == cfg


def test_read_mapping_errors_and_outside_relpath(tmp_path: Path):
    from referia.config.site import _read_mapping

    missing = tmp_path / "gone.yml"
    assert _read_mapping(missing) == {}
    bad = tmp_path / "_config.yml"
    bad.write_text(":\n  - not yaml", encoding="utf-8")
    assert _read_mapping(bad) == {}
    listed = tmp_path / "list.yml"
    listed.write_text("- a\n", encoding="utf-8")
    assert _read_mapping(listed) == {}
    (tmp_path / "_config.yml").write_text(
        "ghub:\n  edit: true\n  organization: mlatcl\n  repository: r\n",
        encoding="utf-8",
    )
    outside = Path("/tmp/elsewhere.md")
    site = load_site_constants(tmp_path, config_path=outside, stop=tmp_path)
    assert site["github_edit_url"].endswith("/elsewhere.md")
