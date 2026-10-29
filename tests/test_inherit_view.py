"""CIP-0018 stacked inherit view — parse, layers, specs, web render, writes."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from referia.config.inherit_view import (
    PARENT_ASSESSOR_LINK_KEY,
    InheritViewOptions,
    compose_viewer_review,
    inherited_readonly_fields,
    parse_inherit_view_options,
    view_options_for_interface,
)
from referia.config.interface import Interface
from referia.web.app import create_app
from referia.web.render import render_form, render_viewer_tree


def _cfg(title: str, extra: str = "") -> str:
    return (
        "referia_config_version: 1\n"
        f"title: {title}\n"
        "strict_columns: false\n"
        "allocation:\n"
        "  type: fake\n"
        "  index: name\n"
        "  nrows: 1\n"
        "  cols:\n"
        "    - name\n"
        f"{extra}"
    )


def _write_chain(tmp_path: Path, *, child_extra: str = "") -> Path:
    gp = tmp_path / "grandparent"
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    gp.mkdir()
    parent.mkdir()
    child.mkdir()
    (gp / "_referia.yml").write_text(
        _cfg(
            "Grandparent",
            "viewer:\n"
            "  - liquid: GP viewer\n"
            "review:\n"
            "  - type: Textarea\n"
            "    field: gpComment\n"
            "    args:\n"
            "      description: GP comment\n",
        )
    )
    (parent / "_referia.yml").write_text(
        _cfg(
            "Parent",
            "inherit:\n"
            "  directory: ../grandparent\n"
            "  writable: false\n"
            "viewer:\n"
            "  - liquid: Parent viewer\n"
            "review:\n"
            "  - type: Textarea\n"
            "    field: parentComment\n"
            "    args:\n"
            "      description: Parent comment\n",
        )
    )
    (child / "_referia.yml").write_text(
        _cfg(
            "Child",
            "inherit:\n"
            "  directory: ../parent\n"
            "  writable: false\n"
            f"{child_extra}"
            "viewer:\n"
            "  - liquid: Child viewer\n"
            "review:\n"
            "  - type: Textarea\n"
            "    field: childComment\n"
            "    args:\n"
            "      description: Child comment\n",
        )
    )
    return child


def _load_child(child: Path) -> Interface:
    return Interface.from_file(
        "_referia.yml",
        str(child),
        allowed_roots=[str(child.parent.resolve())],
    )


class TestParseInheritViewOptions:
    def test_default_is_link(self):
        opts = parse_inherit_view_options()
        assert opts.compose == "link"
        assert opts.inherit_viewer is True
        assert opts.inherit_review is True
        assert opts.source == "default"

    def test_yaml_stacked_without_query(self):
        opts = parse_inherit_view_options(yaml_compose="stacked")
        assert opts.compose == "stacked"
        assert opts.source == "yaml"

    def test_query_overrides_yaml(self):
        opts = parse_inherit_view_options(
            query={"compose": "link"}, yaml_compose="stacked"
        )
        assert opts.compose == "link"
        assert opts.source == "query"

    def test_query_stacked(self):
        opts = parse_inherit_view_options(query={"compose": "stacked"})
        assert opts.compose == "stacked"

    def test_case_insensitive(self):
        opts = parse_inherit_view_options(query={"Compose": "STACKED"})
        assert opts.compose == "stacked"

    def test_unknown_compose_falls_back(self, caplog):
        with caplog.at_level(logging.WARNING):
            opts = parse_inherit_view_options(query={"compose": "not-a-mode"})
        assert opts.compose == "link"
        assert "compose" in caplog.text.lower() or caplog.records

    def test_writable_query_ignored(self, caplog):
        with caplog.at_level(logging.WARNING):
            opts = parse_inherit_view_options(
                query={"compose": "stacked", "writable": "true"}
            )
        assert opts.compose == "stacked"
        assert "writable" in caplog.text

    def test_inherit_review_zero(self):
        opts = parse_inherit_view_options(
            query={"compose": "stacked", "inherit_review": "0"}
        )
        assert opts.inherit_review is False
        assert opts.inherit_viewer is True

    def test_invalid_bool_defaults(self):
        opts = parse_inherit_view_options(
            query={"compose": "stacked", "inherit_review": "maybe"}
        )
        assert opts.inherit_review is True

    def test_query_string_form(self):
        opts = parse_inherit_view_options(query="compose=stacked&inherit_viewer=0")
        assert opts.compose == "stacked"
        assert opts.inherit_viewer is False


class TestInterfaceLayers:
    def test_no_parent_is_self_only(self, tmp_path):
        d = tmp_path / "solo"
        d.mkdir()
        (d / "_referia.yml").write_text(_cfg("Solo"))
        iface = Interface.from_file(
            "_referia.yml", str(d), allowed_roots=[str(tmp_path)]
        )
        layers = iface.interface_layers()
        assert len(layers) == 1
        assert layers[0].title == "Solo"
        assert layers[0].is_self is True

    def test_three_config_chain_root_first(self, tmp_path):
        child = _write_chain(tmp_path)
        iface = _load_child(child)
        layers = iface.interface_layers()
        assert [layer.title for layer in layers] == [
            "Grandparent",
            "Parent",
            "Child",
        ]
        assert layers[-1].is_self is True
        assert layers[0].is_self is False
        assert any("GP viewer" in str(e) for e in layers[0].viewer)
        assert any(
            isinstance(e, dict) and e.get("field") == "gpComment"
            for e in layers[0].review
        )
        assert any(
            isinstance(e, dict) and e.get("field") == "childComment"
            for e in layers[-1].review
        )
        # Parent review is this node's _data, not merged __getitem__.
        assert not any(
            isinstance(e, dict) and e.get("field") == "gpComment"
            for e in layers[1].review
        )

    def test_webreviewer_uses_interface_from_file(self, tmp_path):
        """Prerequisite: WebReviewer loads inherit via Interface.from_file."""
        from referia.assess.web_review import WebReviewer

        child = _write_chain(tmp_path)
        reviewer = WebReviewer("_referia.yml", str(child))
        assert reviewer._interface._parent is not None
        assert reviewer._interface._parent._parent is not None
        layers = reviewer._interface.interface_layers()
        assert len(layers) == 3


class TestComposeSpecs:
    def test_link_mode_returns_none(self, tmp_path):
        iface = _load_child(_write_chain(tmp_path))
        assert (
            compose_viewer_review(iface, InheritViewOptions(compose="link"))
            is None
        )

    def test_stacked_order_and_titles(self, tmp_path):
        iface = _load_child(_write_chain(tmp_path))
        viewer, review = compose_viewer_review(
            iface, InheritViewOptions(compose="stacked")
        )
        assert [s.get("title") for s in viewer if s.get("inherited")] == [
            "Grandparent",
            "Parent",
        ]
        assert [s.get("title") for s in review if s.get("inherited")] == [
            "Grandparent",
            "Parent",
        ]
        assert any(
            isinstance(e, dict) and "Child viewer" in str(e)
            for e in viewer
            if not e.get("inherited")
        )
        assert any(
            isinstance(e, dict) and e.get("field") == "childComment"
            for e in review
            if not e.get("inherited")
        )
        assert not any(
            isinstance(e, dict) and e.get(PARENT_ASSESSOR_LINK_KEY)
            for e in viewer
        )

    def test_inherit_review_zero_omits_ancestor_review(self, tmp_path):
        iface = _load_child(_write_chain(tmp_path))
        _, review = compose_viewer_review(
            iface,
            InheritViewOptions(compose="stacked", inherit_review=False),
        )
        assert not any(s.get("inherited") for s in review if isinstance(s, dict))
        assert any(
            isinstance(e, dict) and e.get("field") == "childComment" for e in review
        )

    def test_link_webreviewer_has_parent_link_not_inherited_section(self, tmp_path):
        from referia.assess.web_review import WebReviewer

        child = _write_chain(tmp_path)
        reviewer = WebReviewer("_referia.yml", str(child))
        opts = InheritViewOptions(compose="link")
        viewer = reviewer.get_viewer_specs(view_options=opts)
        review = reviewer.get_review_specs(view_options=opts)
        joined = " ".join(str(s) for s in viewer)
        assert "Parent assesser" in joined
        assert not any(s.get("inherited") for s in review if isinstance(s, dict))
        assert not any(
            s.get("title") == "Grandparent" for s in review if isinstance(s, dict)
        )

    def test_stacked_webreviewer_wraps_ancestors(self, tmp_path):
        from referia.assess.web_review import WebReviewer

        child = _write_chain(tmp_path)
        reviewer = WebReviewer("_referia.yml", str(child))
        opts = InheritViewOptions(compose="stacked")
        viewer = reviewer.get_viewer_specs(view_options=opts)
        review = reviewer.get_review_specs(view_options=opts)
        assert viewer[0]["title"] == "Grandparent"
        assert viewer[0]["inherited"] is True
        assert review[0]["title"] == "Grandparent"
        assert review[0].get("writable") is False

    def test_readonly_fields_exclude_child(self, tmp_path):
        iface = _load_child(_write_chain(tmp_path))
        fields = inherited_readonly_fields(
            iface, InheritViewOptions(compose="stacked")
        )
        assert "gpComment" in fields
        assert "parentComment" in fields
        assert "childComment" not in fields


class TestRenderInherited:
    def test_inherited_section_is_readonly_and_has_parent_link(self):
        specs = [
            {
                "type": "Section",
                "title": "Parent",
                "inherited": True,
                "writable": False,
                "parent_href": "../parent/?index=Alice&compose=stacked",
                "entries": [
                    {
                        "type": "Textarea",
                        "field": "parentComment",
                        "args": {"description": "Parent comment"},
                    }
                ],
            },
            {
                "type": "Textarea",
                "field": "childComment",
                "args": {"description": "Child comment"},
            },
        ]
        html = render_form(specs, {"parentComment": "old", "childComment": "mine"})
        assert "inherited-section" in html
        assert "open in parent" in html
        assert "../parent/?index=Alice" in html
        assert "readonly" in html
        assert 'hx-post="/field/parentComment"' not in html
        assert 'hx-post="/field/childComment"' in html

    def test_viewer_tree_wraps_sections(self):
        specs = [
            {
                "type": "Section",
                "title": "Grandparent",
                "inherited": True,
                "parent_href": "../grandparent/",
                "entries": [{"liquid": "GP viewer"}],
            },
            {"liquid": "Child viewer"},
        ]
        blocks = render_viewer_tree(specs, lambda spec: f"LEAF:{spec}")
        assert "inherited-section" in blocks[0]
        assert "open in parent" in blocks[0]
        assert "LEAF:" in blocks[0]
        assert 'data-section-key="viewer/0/grandparent"' in blocks[0]
        assert blocks[1].startswith("LEAF:")

    def test_viewer_tree_hides_section_when_visible_if_false(self):
        specs = [
            {
                "type": "Section",
                "title": "Chapter 8",
                "inherited": True,
                "visible_if": "ch8Present",
                "entries": [{"liquid": "ch8 viewer"}],
            },
            {"liquid": "Child viewer"},
        ]
        blocks = render_viewer_tree(
            specs,
            lambda spec: f"LEAF:{spec.get('liquid')}",
            data={"ch8Present": False},
        )
        assert "display:none" in blocks[0]
        assert "LEAF:ch8 viewer" in blocks[0]
        assert "display:none" not in blocks[1]

    def test_viewer_tree_shows_section_when_visible_if_true(self):
        specs = [
            {
                "type": "Section",
                "title": "Chapter 8",
                "visible_if": "ch8Present",
                "entries": [{"liquid": "ch8 viewer"}],
            }
        ]
        blocks = render_viewer_tree(
            specs,
            lambda spec: f"LEAF:{spec.get('liquid')}",
            data={"ch8Present": True},
        )
        assert "display:none" not in blocks[0]
        assert "LEAF:ch8 viewer" in blocks[0]

    def test_viewer_tree_section_keys_are_stable_and_prefixed(self):
        specs = [
            {
                "type": "Section",
                "title": "Pairwise EMD",
                "entries": [{"liquid": "caption"}, {"type": "PlotlyFigure", "field": "emd"}],
            },
            {
                "type": "Section",
                "title": "Radar",
                "args": {"open": False},
                "entries": [{"liquid": "radar"}],
            },
        ]
        blocks = render_viewer_tree(specs, lambda spec: f"LEAF:{spec.get('field', spec.get('liquid'))}")
        assert 'data-section-key="viewer/0/pairwise-emd"' in blocks[0]
        assert 'data-section-key="viewer/1/radar"' in blocks[1]
        assert blocks[0].startswith("<details")
        assert ' open>' in blocks[0]
        assert " open>" not in blocks[1]
        assert "LEAF:emd" in blocks[0]
        assert "LEAF:radar" in blocks[1]


class TestWebRoutesInheritView:
    def test_base_html_copies_view_params(self, tmp_path):
        child = _write_chain(tmp_path)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "inherit_viewer" in resp.text
        assert "inherit_review" in resp.text
        assert "compose" in resp.text

    def test_default_page_is_link_view(self, tmp_path):
        child = _write_chain(tmp_path)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            resp = client.get("/")
        assert "Parent assesser" in resp.text
        assert "inherited-section" not in resp.text
        assert "Show inherited" in resp.text
        assert "compose=stacked" in resp.text

    def test_compose_stacked_shows_ancestors(self, tmp_path):
        child = _write_chain(tmp_path)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            resp = client.get("/", params={"compose": "stacked"})
        assert resp.status_code == 200
        assert "inherited-section" in resp.text
        assert "Grandparent" in resp.text
        assert "Hide inherited" in resp.text
        assert "compose=link" in resp.text
        pos_gp = resp.text.find("Grandparent")
        pos_parent = resp.text.find(">Parent<")
        pos_child = resp.text.find("childComment")
        assert pos_gp != -1
        assert pos_gp < pos_child

    def test_unknown_compose_is_link_not_error(self, tmp_path):
        child = _write_chain(tmp_path)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            resp = client.get("/", params={"compose": "not-a-mode"})
        assert resp.status_code == 200
        assert "inherited-section" not in resp.text
        assert "not-a-mode" not in resp.text

    def test_writable_query_does_not_enable_writes(self, tmp_path):
        child = _write_chain(tmp_path)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            resp = client.get(
                "/", params={"compose": "stacked", "writable": "true"}
            )
            assert "readonly" in resp.text
            reviewer = app.state.reviewer
            try:
                before = reviewer.get_value("gpComment")
            except Exception:
                before = object()
            post = client.post(
                "/field/gpComment",
                data={"gpComment": "should-not-stick"},
                params={"compose": "stacked", "writable": "true"},
            )
            assert post.status_code == 200
            assert "status-error" in post.text or "failed" in post.text.lower()
            try:
                after = reviewer.get_value("gpComment")
            except Exception:
                after = before
            assert after == before

    def test_stacked_survives_record_fetch(self, tmp_path):
        child = _write_chain(tmp_path)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            idx = app.state.reviewer.get_index()
            resp = client.get(
                "/record", params={"index": idx, "compose": "stacked"}
            )
        assert resp.status_code == 200
        assert "inherited-section" in resp.text

    def test_inherit_review_zero_keeps_child_review(self, tmp_path):
        child = _write_chain(tmp_path)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            resp = client.get(
                "/", params={"compose": "stacked", "inherit_review": "0"}
            )
        assert "childComment" in resp.text or "Child comment" in resp.text
        assert "gpComment" not in resp.text

    def test_yaml_compose_stacked_is_author_default(self, tmp_path):
        child = _write_chain(tmp_path)
        text = (child / "_referia.yml").read_text()
        text = text.replace(
            "  writable: false\n",
            "  writable: false\n  compose: stacked\n",
            1,
        )
        (child / "_referia.yml").write_text(text)
        iface = _load_child(child)
        opts = view_options_for_interface(iface, query=None)
        assert opts.compose == "stacked"
        assert opts.source == "yaml"

    def test_inline_list_still_lists_rows(self, tmp_path):
        child = _write_chain(tmp_path)
        text = (child / "_referia.yml").read_text()
        text += "display:\n  layout: inline_list\n"
        (child / "_referia.yml").write_text(text)
        app = create_app(user_file="_referia.yml", directory=str(child))
        with TestClient(app) as client:
            resp = client.get("/", params={"compose": "stacked"})
        assert resp.status_code == 200
        assert "inline-list-page" in resp.text


class TestJupyterYamlCompose:
    def test_jupyter_follows_yaml_not_query(self, tmp_path):
        child = _write_chain(tmp_path)
        iface = _load_child(child)
        # Query is ignored for Jupyter (callers pass query=None).
        opts = view_options_for_interface(
            iface, query={"compose": "stacked"}
        )
        # This helper *does* honour query when passed; Jupyter passes None.
        web_opts = view_options_for_interface(iface, query={"compose": "stacked"})
        assert web_opts.compose == "stacked"
        jupyter_opts = view_options_for_interface(iface, query=None)
        assert jupyter_opts.compose == "link"

    def test_create_viewer_accepts_section(self):
        from referia.assess.review import Reviewer
        from lynguine.assess.display import WidgetCluster

        reviewer = MagicMock()
        reviewer._widgets = WidgetCluster(name="root", parent=reviewer)
        cluster = Reviewer._create_viewer(
            reviewer,
            [
                {
                    "type": "Section",
                    "title": "Parent",
                    "inherited": True,
                    "entries": [{"liquid": "hello"}],
                }
            ],
        )
        assert cluster is not None
