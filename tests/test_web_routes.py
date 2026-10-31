"""Integration tests for the referia web HTMX routes.

Each test patches ``WebReviewer`` at the module level so no real data files
are needed.  The FastAPI ``TestClient`` drives the full HTTP stack (routing,
templates, ``render_widget`` / ``render_form``) while ``WebReviewer`` is
replaced with a lightweight ``MagicMock``.

Fixture design
--------------
``mock_reviewer`` — returns a ``MagicMock`` pre-configured with three
    index values (``"alice"``, ``"bob"``, ``"carol"``), a viewer spec, two
    review widget specs (``Textarea`` + ``Slider``), and sensible defaults
    for every method called by the routes.

``client`` — patches ``referia.assess.web_review.WebReviewer`` so that the
    app startup handler returns ``mock_reviewer``, then yields a
    ``TestClient`` for that app.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from referia.web.app import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VIEWER_SPECS = [
    {"type": "Markdown", "display": "## {Name}"},
]

_REVIEW_SPECS = [
    {"type": "Textarea", "field": "Comment", "description": "Comments", "rows": 4},
    {"type": "IntSlider", "field": "Score", "description": "Score", "min": 0, "max": 10, "step": 1},
    {"type": "SaveButton", "description": "Save"},
]

_INDICES = ["alice", "bob", "carol"]


def _build_mock_reviewer() -> MagicMock:
    """Return a fully-configured WebReviewer mock."""
    reviewer = MagicMock()
    reviewer.index_list.return_value = list(_INDICES)
    reviewer.get_index.return_value = "alice"

    reviewer.get_viewer_specs.return_value = list(_VIEWER_SPECS)
    reviewer.get_review_specs.return_value = list(_REVIEW_SPECS)
    reviewer.get_widget_specs.return_value = list(_VIEWER_SPECS) + list(_REVIEW_SPECS)

    reviewer.render_viewer_html.return_value = "<div class='viewer'>Alice info</div>"

    reviewer.get_value.return_value = ""
    reviewer.get_row_data.return_value = {}
    reviewer.affected_widgets.return_value = {"Comment", "Score"}
    reviewer.list_pdf_entries.return_value = []
    reviewer.list_url_entries.return_value = []
    reviewer.list_document_entries.return_value = []
    reviewer._directory = "/tmp"
    return reviewer


@pytest.fixture
def mock_reviewer() -> MagicMock:
    return _build_mock_reviewer()


@pytest.fixture
def client(mock_reviewer: MagicMock):
    """FastAPI TestClient with WebReviewer replaced by mock_reviewer."""
    with patch(
        "referia.assess.web_review.WebReviewer",
        return_value=mock_reviewer,
    ):
        app = create_app(user_file="_referia.yml", directory="/tmp")
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


class TestGetRoot:
    def test_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_content_type_is_html(self, client):
        response = client.get("/")
        assert "text/html" in response.headers["content-type"]

    def test_html_contains_index_selector(self, client):
        response = client.get("/")
        assert 'id="index-select"' in response.text

    def test_html_lists_all_indices_as_options(self, client):
        response = client.get("/")
        for name in _INDICES:
            assert name in response.text

    def test_html_contains_review_field_ids(self, client):
        response = client.get("/")
        assert 'id="widget-Comment"' in response.text
        assert 'id="widget-Score"' in response.text

    def test_html_contains_htmx_post_for_comment(self, client):
        response = client.get("/")
        assert 'hx-post="/field/Comment"' in response.text

    def test_html_contains_htmx_post_for_score(self, client):
        response = client.get("/")
        assert 'hx-post="/field/Score"' in response.text

    def test_html_contains_save_button(self, client):
        response = client.get("/")
        assert 'hx-post="/save"' in response.text

    def test_save_button_has_no_hx_include(self, client):
        """Save button must NOT use hx-include.  Each field posts its own value
        via per-field change/blur/mouseup events; Save just flushes to disk."""
        response = client.get("/")
        assert 'hx-include="#review-form"' not in response.text

    def test_html_contains_status_bar(self, client):
        response = client.get("/")
        assert 'id="status-bar"' in response.text
        assert 'aria-live="polite"' in response.text
        assert "longOpLabel" in response.text
        assert "completeLongOpBar" in response.text
        assert "status-busy" in response.text
        assert "Saving" in response.text
        assert "Reloaded" in response.text

    def test_html_keeps_populate_progress_chip_during_updating_all(self, client):
        """CIP-0021 chip and the busy 'Updating all…' overlay share the bar.

        Rolling populate-all POSTs must not replace #populate-all-progress
        with the indeterminate label, and must not 3s-hide while chaining.
        """
        html = client.get("/").text
        assert "isPopulateAllPath" in html
        assert "populateAllChipActive" in html
        assert 'querySelector("#populate-all-progress")' in html
        assert "Updating all" in html

    def test_html_includes_htmx_script(self, client):
        response = client.get("/")
        assert "htmx" in response.text

    def test_html_includes_mathjax_typesetter(self, client):
        """Jupyter Markdown widgets use HTMLMath; the web page must load MathJax."""
        response = client.get("/")
        html = response.text
        assert "mathjax@3" in html
        assert "tex-chtml.js" in html
        assert "MathJax.typesetPromise" in html
        assert "inlineMath" in html


# ---------------------------------------------------------------------------
# GET /record
# ---------------------------------------------------------------------------


class TestGetRecord:
    def test_returns_200(self, client, mock_reviewer):
        response = client.get("/record", params={"index": "bob"})
        assert response.status_code == 200

    def test_calls_set_index_with_requested_value(self, client, mock_reviewer):
        client.get("/record", params={"index": "bob"})
        mock_reviewer.set_index.assert_called_once_with("bob")

    def test_returns_panel_fragment_without_full_page(self, client):
        response = client.get("/record", params={"index": "bob"})
        # Fragment should not contain the outer <html> shell
        assert "<html" not in response.text

    def test_fragment_contains_index_selector(self, client):
        response = client.get("/record", params={"index": "alice"})
        assert 'id="index-select"' in response.text

    def test_fragment_contains_review_widgets(self, client):
        response = client.get("/record", params={"index": "alice"})
        assert 'id="widget-Comment"' in response.text

    def test_no_index_param_does_not_call_set_index(self, client, mock_reviewer):
        client.get("/record")
        mock_reviewer.set_index.assert_not_called()

    def test_missing_index_returns_404(self, client, mock_reviewer):
        mock_reviewer.set_index.side_effect = KeyError('Index "99" not found in data')
        response = client.get("/record", params={"index": "99"})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /indices
# ---------------------------------------------------------------------------


class TestGetIndices:
    def test_returns_200(self, client):
        response = client.get("/indices")
        assert response.status_code == 200

    def test_returns_select_element(self, client):
        response = client.get("/indices")
        assert "<select" in response.text
        assert 'id="index-select"' in response.text

    def test_all_indices_present_as_options(self, client):
        response = client.get("/indices")
        for name in _INDICES:
            assert name in response.text


# ---------------------------------------------------------------------------
# POST /field/{column}
# ---------------------------------------------------------------------------


class TestPostField:
    def test_returns_200(self, client):
        response = client.post("/field/Comment", data={"Comment": "Great!"})
        assert response.status_code == 200

    def test_calls_set_value_with_submitted_data(self, client, mock_reviewer):
        client.post("/field/Comment", data={"Comment": "Great!"})
        mock_reviewer.set_value.assert_called_once_with("Comment", "Great!")

    def test_response_contains_success_status(self, client):
        response = client.post("/field/Comment", data={"Comment": "Well done"})
        assert "Updated" in response.text or "&#10003;" in response.text

    def test_response_contains_oob_swaps_for_affected_widgets(self, client, mock_reviewer):
        mock_reviewer.affected_widgets.return_value = {"Comment", "Score"}
        response = client.post("/field/Comment", data={"Comment": "x"})
        # Dependents are OOB-swapped; the triggering field is not (focus preserve)
        assert 'id="widget-Comment"' not in response.text
        assert 'id="widget-Score"' in response.text

    def test_oob_swaps_omit_triggering_column(self, client, mock_reviewer):
        mock_reviewer.affected_widgets.return_value = {"Comment"}
        response = client.post("/field/Comment", data={"Comment": "x"})
        assert 'id="widget-Comment"' not in response.text
        assert "Updated" in response.text or "&#10003;" in response.text

    def test_oob_swaps_carry_hx_swap_oob_attribute(self, client, mock_reviewer):
        mock_reviewer.affected_widgets.return_value = {"Comment", "Score"}
        response = client.post("/field/Comment", data={"Comment": "x"})
        assert 'hx-swap-oob="true"' in response.text
        assert 'id="widget-Score"' in response.text

    def test_field_controls_use_focus_scroll_false(self, client):
        response = client.get("/")
        assert 'hx-swap="innerHTML focus-scroll:false"' in response.text

    def test_unknown_column_does_not_crash(self, client, mock_reviewer):
        mock_reviewer.set_value.side_effect = KeyError("no such column")
        response = client.post("/field/Nonexistent", data={"Nonexistent": "x"})
        assert response.status_code == 200
        assert "failed" in response.text.lower()
        assert "no such column" not in response.text

    def test_checkbox_field_coerces_truthy_value(self, client, mock_reviewer):
        mock_reviewer.get_widget_specs.return_value = [
            {"type": "Checkbox", "field": "Flag", "description": "Flag"},
        ]
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "Flag", "description": "Flag"},
        ]
        mock_reviewer.affected_widgets.return_value = {"Flag"}
        client.post("/field/Flag", data={"Flag": "on"})
        # set_value should have been called with a bool True
        args = mock_reviewer.set_value.call_args
        assert args[0][0] == "Flag"
        assert args[0][1] is True

    def test_missing_checkbox_value_coerces_to_false(self, client, mock_reviewer):
        mock_reviewer.get_widget_specs.return_value = [
            {"type": "Checkbox", "field": "Flag", "description": "Flag"},
        ]
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "Flag", "description": "Flag"},
        ]
        mock_reviewer.affected_widgets.return_value = {"Flag"}
        # When a checkbox is unchecked, browsers omit it from the POST body
        client.post("/field/Flag", data={})
        args = mock_reviewer.set_value.call_args
        assert args[0][1] is False

    def test_field_update_includes_document_actions_oob(self, client, mock_reviewer):
        """Interview-gated Create Email must OOB-refresh with the field update."""
        mock_reviewer.list_document_entries.side_effect = lambda section="documents": (
            [
                {
                    "n": 0,
                    "type": "email",
                    "label": "Create Email",
                    "summary": False,
                    "section": "documents",
                    "visible_if": "Interview",
                }
            ]
            if section == "documents"
            else []
        )
        mock_reviewer.get_row_data.return_value = {"Interview": True, "Comment": "x"}
        mock_reviewer.affected_widgets.return_value = set()
        response = client.post("/field/Interview", data={"Interview": "true"})
        assert response.status_code == 200
        assert 'id="nav-document-actions"' in response.text
        assert 'hx-swap-oob="true"' in response.text
        assert "Create Email" in response.text

    def test_field_update_hides_gated_document_action(self, client, mock_reviewer):
        mock_reviewer.list_document_entries.side_effect = lambda section="documents": (
            [
                {
                    "n": 0,
                    "type": "email",
                    "label": "Create Email",
                    "summary": False,
                    "section": "documents",
                    "visible_if": "Interview",
                }
            ]
            if section == "documents"
            else []
        )
        mock_reviewer.get_row_data.return_value = {"Interview": False}
        mock_reviewer.affected_widgets.return_value = set()
        response = client.post("/field/Interview", data={})
        assert response.status_code == 200
        assert 'id="nav-document-actions"' in response.text
        assert 'hx-swap-oob="true"' in response.text
        assert "Create Email" not in response.text

    def test_viewer_source_oob_refreshes_trigger_column(self, client, mock_reviewer):
        """CIP-0011: plot writes must OOB-refresh the review widget for that field."""
        mock_reviewer.affected_widgets.return_value = set()
        mock_reviewer.get_value.return_value = "topic-1"
        response = client.post(
            "/field/Comment",
            data={"Comment": "from-plot", "source": "viewer"},
        )
        assert response.status_code == 200
        assert 'id="widget-Comment"' in response.text
        assert 'hx-swap-oob="true"' in response.text

    def test_field_update_oob_refreshes_highlight_viewers(self, client, mock_reviewer):
        mock_reviewer.affected_widgets.return_value = set()
        mock_reviewer.get_viewer_specs.return_value = [
            {
                "type": "PlotlyFigure",
                "field": "fig",
                "highlight": {"from_field": "Comment"},
            }
        ]
        mock_reviewer.get_value.side_effect = lambda col: (
            {"data": [{"type": "scatter", "x": [1], "y": [2]}], "layout": {}}
            if col == "fig"
            else "t1"
        )
        response = client.post("/field/Comment", data={"Comment": "t1"})
        assert response.status_code == 200
        assert 'id="plotly-spec-0"' in response.text
        assert 'hx-swap-oob="true"' in response.text
        assert "plotly-spec" in response.text
        mock_reviewer.render_viewer_html.assert_not_called()


# ---------------------------------------------------------------------------
# CIP-0011 viewer OOB helpers
# ---------------------------------------------------------------------------


class TestViewerOobHelpers:
    def test_make_viewer_oob_marks_plotly_and_image(self):
        from referia.web.routes import _make_viewer_oob

        plotly = '<div class="viewer viewer-plotly" id="viewer-plotly-0"></div>'
        assert 'hx-swap-oob="true"' in _make_viewer_oob(plotly)
        filled = (
            '<div class="viewer viewer-plotly viewer-plotly--fill" '
            'id="viewer-plotly-0"></div>'
        )
        assert 'hx-swap-oob="true"' in _make_viewer_oob(filled)
        image = '<div class="viewer viewer-image" id="viewer-image-1"></div>'
        assert 'hx-swap-oob="true"' in _make_viewer_oob(image)
        # Liquid catalogue / intro viewers also OOB-refresh after naming.
        markdown = '<div class="viewer viewer-markdown">x</div>'
        assert 'hx-swap-oob="true"' in _make_viewer_oob(markdown)
        html = '<div class="viewer viewer-html">y</div>'
        assert 'hx-swap-oob="true"' in _make_viewer_oob(html)
        untouched = '<div class="viewer viewer-other">z</div>'
        assert _make_viewer_oob(untouched) == untouched

    def test_viewer_highlight_oobs_filters_by_field(self):
        from referia.web.routes import _viewer_highlight_oobs

        reviewer = MagicMock()
        reviewer.get_viewer_specs.return_value = [
            {"type": "Markdown", "liquid": "x"},
            "skip-non-dict",
            {
                "type": "PlotlyFigure",
                "field": "fig",
                "highlight": {"from_field": "selected_topic"},
            },
            {
                "type": "PlotlyFigure",
                "field": "other",
                "highlight": {"from_field": "other_field"},
            },
        ]
        reviewer.get_value.side_effect = lambda col: (
            {"data": [], "layout": {"height": 100}}
            if col == "fig"
            else "B"
        )
        parts = _viewer_highlight_oobs(reviewer, "selected_topic")
        assert len(parts) == 1
        assert 'id="plotly-spec-1"' in parts[0]
        assert 'hx-swap-oob="true"' in parts[0]
        reviewer.render_viewer_html.assert_not_called()

    def test_viewer_highlight_oobs_walks_section_leaves(self):
        from referia.web.routes import _viewer_highlight_oobs

        reviewer = MagicMock()
        reviewer.get_viewer_specs.return_value = [
            {"liquid": "intro"},
            {
                "type": "Section",
                "title": "Pairwise EMD",
                "entries": [
                    {"liquid": "caption"},
                    {
                        "type": "PlotlyFigure",
                        "field": "emd_heatmap_spec",
                    },
                ],
            },
        ]
        reviewer.get_value.side_effect = lambda col: (
            {"data": [], "layout": {"height": 100}}
            if col == "emd_heatmap_spec"
            else "x"
        )
        parts = _viewer_highlight_oobs(reviewer, "emd_heatmap_spec")
        assert len(parts) == 1
        assert 'id="plotly-spec-2"' in parts[0]
        assert 'hx-swap-oob="true"' in parts[0]
        reviewer.render_viewer_html.assert_not_called()

    def test_viewer_highlight_oobs_refreshes_watched_liquid(self):
        from referia.web.routes import _viewer_highlight_oobs

        reviewer = MagicMock()
        reviewer.get_viewer_specs.return_value = [
            {"liquid": "store status"},
            {
                "liquid": "{{ units }}",
                "watch": ["units"],
                "collapse": {"headings": ["Paragraphs"]},
            },
            {"liquid": "also units", "field": "units"},
        ]
        reviewer.render_viewer_html.side_effect = (
            lambda spec, viewer_index=0: (
                f'<div class="viewer viewer-markdown" '
                f'id="viewer-markdown-{viewer_index}">n={viewer_index}</div>'
            )
        )
        parts = _viewer_highlight_oobs(reviewer, "units")
        assert len(parts) == 2
        assert 'id="viewer-markdown-1"' in parts[0]
        assert 'id="viewer-markdown-2"' in parts[1]
        assert all('hx-swap-oob="true"' in part for part in parts)
        ignored = _viewer_highlight_oobs(reviewer, "notes")
        assert ignored == []

    def test_viewer_highlight_oobs_refreshes_visible_if(self):
        from referia.web.routes import _viewer_highlight_oobs

        reviewer = MagicMock()
        reviewer.get_viewer_specs.return_value = [
            {"liquid": "always"},
            {
                "type": "Markdown",
                "liquid": "Chapter 8",
                "visible_if": "ch8Present",
            },
            {
                "type": "Markdown",
                "liquid": "equals form",
                "visible_if": {"field": "ch8Present", "equals": True},
            },
        ]
        reviewer.render_viewer_html.side_effect = (
            lambda spec, viewer_index=0: (
                f'<div class="viewer viewer-markdown" '
                f'id="viewer-markdown-{viewer_index}">n={viewer_index}</div>'
            )
        )
        parts = _viewer_highlight_oobs(reviewer, "ch8Present")
        assert len(parts) == 2
        assert 'id="viewer-markdown-1"' in parts[0]
        assert 'id="viewer-markdown-2"' in parts[1]
        assert all('hx-swap-oob="true"' in part for part in parts)
        assert _viewer_highlight_oobs(reviewer, "notes") == []

    def test_viewer_highlight_oobs_refreshes_not_form(self):
        from referia.web.routes import _viewer_highlight_oobs

        reviewer = MagicMock()
        reviewer.get_viewer_specs.return_value = [
            {
                "type": "Markdown",
                "visible_if": {"field": "pending_proposal", "not": True},
            },
            {
                "type": "StaticImage",
                "field": "photo",
                "visible_if": "ch8Present",
            },
        ]
        reviewer.render_viewer_html.side_effect = (
            lambda spec, viewer_index=0: (
                f'<div class="viewer viewer-markdown" '
                f'id="viewer-markdown-{viewer_index}" style="display:none">'
                f"n={viewer_index}</div>"
                if spec.get("type") == "Markdown"
                else (
                    f'<div class="viewer viewer-image" '
                    f'id="viewer-image-{viewer_index}" style="display:none">'
                    f'<img src="x.png" alt="viewer image" /></div>'
                )
            )
        )
        pending = _viewer_highlight_oobs(reviewer, "pending_proposal")
        assert len(pending) == 1
        assert 'id="viewer-markdown-0"' in pending[0]
        assert 'hx-swap-oob="true"' in pending[0]
        assert "display:none" in pending[0]

        photo = _viewer_highlight_oobs(reviewer, "ch8Present")
        assert len(photo) == 1
        assert 'id="viewer-image-1"' in photo[0]
        assert 'hx-swap-oob="true"' in photo[0]

    def test_viewer_source_without_trigger_spec_skips_widget_oob(
        self, client, mock_reviewer
    ):
        """source=viewer with no matching review widget still returns OK."""
        mock_reviewer.affected_widgets.return_value = set()
        mock_reviewer.get_widget_specs.return_value = []
        mock_reviewer.get_viewer_specs.return_value = []
        response = client.post(
            "/field/Orphan",
            data={"Orphan": "x", "source": "viewer"},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# _find_spec / document-actions OOB helpers
# ---------------------------------------------------------------------------


class TestFindSpecSkipsNonRenderers:
    """Compute-like specs must not steal the OOB refresh from real widgets."""

    def test_prefers_textarea_over_compute_dict(self):
        from referia.web.routes import _find_spec

        reviewer = MagicMock()
        reviewer.get_widget_specs.return_value = [
            {
                "field": "Email Comment",
                "function": "render_liquid",
                "args": {"template": "x"},
            },
            {
                "type": "Textarea",
                "field": "Email Comment",
                "visible_if": "Interview",
                "args": {"description": "Email Comment"},
            },
        ]
        spec = _find_spec(reviewer, "Email Comment")
        assert spec is not None
        assert spec["type"] == "Textarea"

    def test_skips_populate_button(self):
        from referia.web.routes import _find_spec

        reviewer = MagicMock()
        reviewer.get_widget_specs.return_value = [
            {"type": "PopulateButton", "field": "Summary", "args": {}},
            {"type": "Textarea", "field": "Summary", "args": {}},
        ]
        spec = _find_spec(reviewer, "Summary")
        assert spec["type"] == "Textarea"

    def test_returns_none_when_only_compute(self):
        from referia.web.routes import _find_spec

        reviewer = MagicMock()
        reviewer.get_widget_specs.return_value = [
            {"field": "Email Comment", "function": "render_liquid"},
        ]
        assert _find_spec(reviewer, "Email Comment") is None


class TestDocumentActionsOob:
    def test_empty_actions_still_emit_stable_oob_target(self):
        from referia.web.routes import _document_actions_oob

        reviewer = MagicMock()
        reviewer.list_document_entries.return_value = []
        html = _document_actions_oob(reviewer, {})
        assert 'id="nav-document-actions"' in html
        assert 'hx-swap-oob="true"' in html

    def test_visible_button_included(self):
        from referia.web.routes import _document_actions_oob

        reviewer = MagicMock()
        reviewer.list_document_entries.side_effect = lambda section="documents": (
            [
                {
                    "n": 0,
                    "type": "email",
                    "label": "Create Email",
                    "summary": False,
                    "visible_if": "Interview",
                }
            ]
            if section == "documents"
            else []
        )
        html = _document_actions_oob(reviewer, {"Interview": True})
        assert "Create Email" in html
        assert 'hx-swap-oob="true"' in html

    def test_inline_list_oob_uses_summary_documents_only(self):
        from referia.web.routes import _document_actions_oob

        reviewer = MagicMock()
        reviewer.get_display_layout.return_value = "inline_list"
        reviewer.list_document_entries.side_effect = lambda section="documents": (
            [
                {
                    "n": 0,
                    "type": "email",
                    "label": "Email feedback",
                    "summary": False,
                }
            ]
            if section == "documents"
            else [
                {
                    "n": 0,
                    "type": "xlsx",
                    "label": "Export scores",
                    "summary": True,
                }
            ]
        )
        html = _document_actions_oob(reviewer, {"markedFlag": "yes"})
        assert "Export scores" in html
        assert "Email feedback" not in html
        assert 'hx-swap-oob="true"' in html

    def test_layout_lookup_failure_keeps_record_documents(self):
        from referia.web.routes import _document_actions_oob

        reviewer = MagicMock()
        reviewer.get_display_layout.side_effect = RuntimeError("no layout")
        reviewer.list_document_entries.side_effect = lambda section="documents": (
            [
                {
                    "n": 0,
                    "type": "email",
                    "label": "Email feedback",
                    "summary": False,
                }
            ]
            if section == "documents"
            else []
        )
        html = _document_actions_oob(reviewer, {})
        assert "Email feedback" in html
        assert 'hx-swap-oob="true"' in html


# ---------------------------------------------------------------------------
# POST /save
# ---------------------------------------------------------------------------


class TestPostSave:
    def test_returns_200(self, client):
        response = client.post("/save", data={"Comment": "ok", "Score": "5"})
        assert response.status_code == 200

    def test_calls_save_flows(self, client, mock_reviewer):
        client.post("/save", data={"Comment": "ok", "Score": "5"})
        mock_reviewer.save_flows.assert_called_once()

    def test_response_contains_saved_confirmation(self, client):
        response = client.post("/save", data={"Comment": "ok", "Score": "5"})
        assert "Saved" in response.text or "&#10003;" in response.text

    def test_save_does_not_call_set_value(self, client, mock_reviewer):
        """Save route must NOT call set_value.

        Each field already posted its own value when the user edited it.
        Save's job is only to flush the in-memory reviewer state to disk
        via save_flows().  Calling set_value here re-runs computes and
        can have unforeseen side-effects.
        """
        client.post("/save", data={"Comment": "looks good", "Score": "7"})
        mock_reviewer.set_value.assert_not_called()

    def test_save_without_form_data_still_calls_save_flows(self, client, mock_reviewer):
        """Even with no form data the save must not crash and must call save_flows."""
        response = client.post("/save", data={})
        assert response.status_code == 200
        mock_reviewer.save_flows.assert_called_once()

    def test_save_failure_returns_200_with_error_message(self, client, mock_reviewer):
        mock_reviewer.save_flows.side_effect = OSError("disk full")
        response = client.post("/save", data={})
        assert response.status_code == 200
        assert "failed" in response.text.lower()
        assert "disk full" not in response.text
        assert "See server log" in response.text


# ---------------------------------------------------------------------------
# _coerce_form_value
# ---------------------------------------------------------------------------


class TestCoerceFormValue:
    """Unit tests for the form-value type-coercion helper."""

    def setup_method(self):
        from referia.web.routes import _coerce_form_value
        self._coerce = _coerce_form_value

    def test_int_slider_string_becomes_int(self):
        spec = {"type": "IntSlider", "field": "Score"}
        assert self._coerce("7", spec) == 7
        assert isinstance(self._coerce("7", spec), int)

    def test_int_slider_zero_string_becomes_zero_int(self):
        spec = {"type": "IntSlider", "field": "Score"}
        assert self._coerce("0", spec) == 0
        assert isinstance(self._coerce("0", spec), int)

    def test_bounded_int_text_string_becomes_int(self):
        spec = {"type": "BoundedIntText", "field": "Score"}
        assert self._coerce("42", spec) == 42

    def test_float_slider_string_becomes_float(self):
        spec = {"type": "FloatSlider", "field": "Confidence"}
        result = self._coerce("0.75", spec)
        assert result == pytest.approx(0.75)
        assert isinstance(result, float)

    def test_checkbox_truthy_value_becomes_true(self):
        spec = {"type": "Checkbox", "field": "Flag"}
        assert self._coerce("on", spec) is True
        assert self._coerce("true", spec) is True

    def test_checkbox_falsy_value_becomes_false(self):
        spec = {"type": "Checkbox", "field": "Flag"}
        assert self._coerce("false", spec) is False
        assert self._coerce("0", spec) is False
        assert self._coerce("", spec) is False
        assert self._coerce(None, spec) is False

    def test_textarea_stays_as_string(self):
        spec = {"type": "Textarea", "field": "Comment"}
        assert self._coerce("hello", spec) == "hello"
        assert isinstance(self._coerce("hello", spec), str)

    def test_none_spec_returns_raw_value_unchanged(self):
        assert self._coerce("anything", None) == "anything"

    def test_unknown_type_returns_raw_value(self):
        spec = {"type": "SomeNewWidget", "field": "x"}
        assert self._coerce("raw", spec) == "raw"

    def test_int_slider_non_numeric_returns_raw(self):
        """Gracefully handle malformed numeric input rather than crashing."""
        spec = {"type": "IntSlider", "field": "Score"}
        assert self._coerce("oops", spec) == "oops"


# ---------------------------------------------------------------------------
# POST /reload
# ---------------------------------------------------------------------------


class TestPostReload:
    def test_returns_200(self, client):
        response = client.post("/reload")
        assert response.status_code == 200

    def test_calls_load_flows(self, client, mock_reviewer):
        client.post("/reload")
        mock_reviewer.load_flows.assert_called_once()

    def test_response_contains_review_panel(self, client):
        response = client.post("/reload")
        assert 'id="index-select"' in response.text
        assert 'hx-swap-oob="true"' in response.text
        assert "Reloaded" in response.text

    def test_reload_failure_omits_exception_text(self, client, mock_reviewer):
        mock_reviewer.load_flows.side_effect = OSError("secret path /tmp/xyz")
        response = client.post("/reload")
        assert response.status_code == 200
        assert "failed" in response.text.lower()
        assert "secret path" not in response.text
        assert "/tmp/xyz" not in response.text


# ---------------------------------------------------------------------------
# POST /populate/{field}
# ---------------------------------------------------------------------------


@pytest.fixture
def populate_client():
    """TestClient with a PopulateButton wired up in the review specs."""
    reviewer = _build_mock_reviewer()
    reviewer.get_review_specs.return_value = [
        {"type": "Textarea", "field": "Summary", "args": {"description": "Summary"}},
        {
            "type": "PopulateButton",
            "field": "SummaryBtn",
            "args": {
                "description": "Generate",
                "target": "Summary",
                "compute": {"field": "Summary", "function": "llm_summarise"},
            },
        },
    ]
    reviewer.get_widget_specs.return_value = reviewer.get_review_specs.return_value
    reviewer.get_value.return_value = "generated text"
    reviewer.run_populate.return_value = None

    with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
        app = create_app(user_file="_referia.yml", directory="/tmp")
        with TestClient(app) as c:
            yield c, reviewer


class TestPopulateStatusHtml:
    """Confirm vs Undo must not share the same status heuristic."""

    def test_confirm_clears_pending_reports_sealed(self):
        from referia.web.routes import _populate_status_html

        reviewer = MagicMock()
        reviewer.get_value.side_effect = lambda c: {
            "pending_proposal": None,
            "topic_keys": ["T0", "T1"],
        }.get(c)
        html = _populate_status_html(
            reviewer,
            ["pending_proposal", "uq_spec", "uq_by_topic", "split_undo"],
        )
        assert "Split sealed" in html
        assert "rejected" not in html

    def test_undo_restores_catalogue_reports_rejected(self):
        from referia.web.routes import _populate_status_html

        reviewer = MagicMock()
        reviewer.get_value.side_effect = lambda c: {
            "pending_proposal": None,
            "topic_keys": ["T0"],
        }.get(c)
        html = _populate_status_html(
            reviewer,
            [
                "pending_proposal",
                "uq_spec",
                "uq_by_topic",
                "topic_keys",
                "responsibilities",
                "focus_topic",
                "topic_labels",
                "split_undo",
            ],
        )
        assert "Split rejected" in html
        assert "sealed" not in html

    def test_reset_reports_k1_seed_not_rejected(self):
        from referia.web.routes import _populate_status_html

        reviewer = MagicMock()
        reviewer.get_value.side_effect = lambda c: {
            "pending_proposal": None,
            "topic_keys": ["T0"],
        }.get(c)
        html = _populate_status_html(
            reviewer,
            [
                "pending_proposal",
                "uq_spec",
                "uq_by_topic",
                "topic_keys",
                "responsibilities",
                "focus_topic",
                "topic_labels",
                "split_undo",
                "selected_phrase",
            ],
            button_field="_reset_grain",
        )
        assert "Reset to k=1 seed" in html
        assert "rejected" not in html
        assert "sealed" not in html

    def test_name_while_pending_does_not_say_proposed(self):
        from referia.web.routes import _populate_status_html

        reviewer = MagicMock()
        reviewer.get_value.side_effect = lambda c: {
            "pending_proposal": {
                "kind": "split",
                "parent": "T1",
                "children": ["T1", "T2"],
                "k_before": 4,
                "k_after": 5,
                "focus": "T1",
            },
            "topic_labels": {
                "T1": "Child A",
                "T2": "Child B",
            },
        }.get(c)
        html = _populate_status_html(
            reviewer,
            [
                "topic_labels",
                "topic_parent",
                "topic_tree",
                "uq_spec",
                "uq_by_topic",
                "pending_proposal",
            ],
        )
        assert "Named pending children" in html
        assert "Child A" in html
        assert "Split proposed" not in html


class TestPostPopulate:
    def test_returns_200(self, populate_client):
        # URL uses the button's own field id; compute still writes args.target.
        client, _ = populate_client
        response = client.post("/populate/SummaryBtn")
        assert response.status_code == 200

    def test_calls_run_populate_with_compute_interface(self, populate_client):
        """Route must call reviewer.run_populate with {"compute": ...}."""
        client, reviewer = populate_client
        client.post("/populate/SummaryBtn")
        reviewer.run_populate.assert_called_once()
        call_arg = reviewer.run_populate.call_args[0][0]
        assert "compute" in call_arg

    def test_oob_response_targets_the_target_field_not_the_button(self, populate_client):
        """OOB swap must refresh the target Textarea, not re-render the PopulateButton."""
        client, _ = populate_client
        response = client.post("/populate/SummaryBtn")
        # The target widget (Summary textarea) should appear in the OOB response
        assert 'id="widget-Summary"' in response.text
        # The button container should NOT appear (it's a different widget)
        assert 'id="widget-SummaryBtn"' not in response.text
        assert 'id="btn-widget-SummaryBtn"' not in response.text

    def test_populate_oob_refreshes_visible_if_populate_buttons(self, populate_client):
        """Confirm/Undo gated on pending_proposal must OOB-refresh after Propose."""
        client, reviewer = populate_client
        reviewer.get_widget_specs.return_value = [
            {"type": "PlotlyFigure", "field": "uq_spec", "args": {}},
            {
                "type": "PopulateButton",
                "field": "_propose_split",
                "args": {
                    "description": "Propose split",
                    "target": "uq_spec",
                    "compute": {
                        "field": ["uq_spec", "pending_proposal"],
                        "function": "subject_grain_propose_split",
                    },
                },
            },
            {
                "type": "PopulateButton",
                "field": "_confirm_split",
                "visible_if": "pending_proposal",
                "args": {
                    "description": "Confirm split",
                    "target": "uq_spec",
                    "compute": {
                        "field": ["pending_proposal"],
                        "function": "subject_grain_confirm_split",
                    },
                },
            },
        ]
        reviewer.get_review_specs.return_value = reviewer.get_widget_specs.return_value
        pending = {"kind": "split", "parent": "T0"}
        row = {"pending_proposal": pending, "uq_spec": {}}
        reviewer.get_row_data.return_value = row
        reviewer.get_value.side_effect = lambda c: row.get(c)
        reviewer.affected_widgets.side_effect = (
            lambda c: {"_confirm_split"} if c == "pending_proposal" else set()
        )

        response = client.post("/populate/_propose_split")
        assert response.status_code == 200
        assert "Confirm split" in response.text
        # Leading underscore stripped in DOM id; Confirm must be visible.
        confirm_start = response.text.index('id="btn-widget-confirm_split"')
        open_div = response.text.rfind("<div", 0, confirm_start)
        open_tag_end = response.text.index(">", open_div)
        opening = response.text[open_div:open_tag_end]
        assert "display:none" not in opening

    def test_legacy_target_url_still_resolves(self, populate_client):
        """POST /populate/{target} still finds the button when no id collision."""
        client, reviewer = populate_client
        response = client.post("/populate/Summary")
        assert response.status_code == 200
        reviewer.run_populate.assert_called_once()

    def test_unknown_populate_field_returns_200(self, populate_client):
        """An unknown field must not crash the server."""
        client, _ = populate_client
        response = client.post("/populate/NonExistent")
        assert response.status_code == 200

    def test_no_compute_spec_returns_warning(self, populate_client):
        """A PopulateButton missing args.compute and top-level function must warn."""
        client, reviewer = populate_client
        reviewer.get_widget_specs.return_value = [
            {
                "type": "PopulateButton",
                "field": "BadBtn",
                "args": {"description": "Bad", "target": "Summary"},
                # no "compute" key and no top-level "function"
            }
        ]
        reviewer.get_review_specs.return_value = reviewer.get_widget_specs.return_value
        response = client.post("/populate/BadBtn")
        assert response.status_code == 200

    def test_simple_format_calls_run_populate(self, populate_client):
        """Simple format (top-level function:) must also call reviewer.run_populate."""
        client, reviewer = populate_client
        reviewer.get_widget_specs.return_value = [
            {"type": "Textarea", "field": "summary", "args": {}},
            {
                "type": "PopulateButton",
                "field": "summary",          # same field as target (simple format)
                "function": "llm_summarise",
                "args": {"text": "{description}"},
                # no nested args.compute
            },
        ]
        reviewer.get_review_specs.return_value = reviewer.get_widget_specs.return_value
        reviewer.get_value.return_value = "generated"

        response = client.post("/populate/summary")
        assert response.status_code == 200
        reviewer.run_populate.assert_called_once()
        call_arg = reviewer.run_populate.call_args[0][0]
        # The simple format should build a compute spec with view_args
        assert "compute" in call_arg
        cs = call_arg["compute"]
        assert cs.get("function") == "llm_summarise"
        assert "view_args" in cs
        # Plain string args must be wrapped as {"display": ...} view spec dicts
        assert cs["view_args"].get("text") == {"display": "{description}"}

    def test_populate_failure_omits_exception_text(self, populate_client):
        client, reviewer = populate_client
        reviewer.run_populate.side_effect = RuntimeError("internal compute boom")
        response = client.post("/populate/Summary")
        assert response.status_code == 200
        assert "failed" in response.text.lower()
        assert "internal compute boom" not in response.text

    def test_populate_honours_form_index(self, populate_client):
        client, reviewer = populate_client
        response = client.post("/populate/SummaryBtn", data={"index": "bob"})
        assert response.status_code == 200
        reviewer.set_index.assert_called_with("bob")
        reviewer.run_populate.assert_called_once()

    def test_inline_list_populate_returns_panel(self, populate_client):
        client, reviewer = populate_client
        reviewer.get_display_layout.return_value = "inline_list"
        reviewer.working_indices.return_value = ["alice"]
        reviewer.get_filter_specs.return_value = []
        reviewer.get_sort_specs.return_value = []
        reviewer.get_filter_state.return_value = {}
        reviewer.get_display_detail_field.return_value = None
        reviewer.get_row_data.return_value = {"title": "Alice"}
        response = client.post("/populate/SummaryBtn", data={"index": "alice"})
        assert response.status_code == 200
        assert 'class="inline-listing"' in response.text
        assert 'id="widget-Summary"' not in response.text

    def test_once_skips_filled_without_refresh_if(self, populate_client):
        client, reviewer = populate_client
        specs = [
            {
                "type": "PopulateButton",
                "field": "_classify",
                "args": {
                    "description": "Classify",
                    "once": True,
                    "refresh_if": "refresh_classification",
                    "target": "grounds_payload",
                    "compute": {
                        "field": ["grounds_payload", "grounds"],
                        "function": "llm_classify_grounds",
                    },
                },
            },
            {
                "type": "Checkbox",
                "field": "refresh_classification",
            },
        ]
        reviewer.get_review_specs.return_value = specs
        reviewer.get_widget_specs.return_value = specs
        row = {
            "grounds_payload": [{"basis": "principle"}],
            "refresh_classification": False,
        }
        reviewer.get_value.side_effect = lambda c: row.get(c, "")
        response = client.post("/populate/_classify")
        assert response.status_code == 200
        reviewer.run_populate.assert_not_called()
        assert "Already classified" in response.text

    def test_once_runs_when_refresh_if_checked_then_clears(self, populate_client):
        client, reviewer = populate_client
        specs = [
            {
                "type": "PopulateButton",
                "field": "_classify",
                "args": {
                    "description": "Classify",
                    "once": True,
                    "refresh_if": "refresh_classification",
                    "target": "grounds_payload",
                    "compute": {
                        "field": ["grounds_payload", "grounds"],
                        "function": "llm_classify_grounds",
                    },
                },
            },
            {
                "type": "Checkbox",
                "field": "refresh_classification",
            },
        ]
        reviewer.get_review_specs.return_value = specs
        reviewer.get_widget_specs.return_value = specs
        row = {
            "grounds_payload": [{"basis": "principle"}],
            "refresh_classification": True,
        }
        reviewer.get_value.side_effect = lambda c: row.get(c, "")
        reviewer.set_value.side_effect = lambda c, v: row.__setitem__(c, v)
        response = client.post("/populate/_classify")
        assert response.status_code == 200
        reviewer.run_populate.assert_called_once()
        assert row["refresh_classification"] is False

    def test_skip_empty_refuses_populate_without_points(self, populate_client):
        client, reviewer = populate_client
        specs = [
            {
                "type": "PopulateButton",
                "field": "_classify",
                "args": {
                    "description": "Classify",
                    "skip_empty": "extraction_phrases",
                    "target": "grounds_payload",
                    "compute": {
                        "field": ["grounds_payload", "grounds"],
                        "function": "llm_classify_grounds",
                    },
                },
            },
        ]
        reviewer.get_review_specs.return_value = specs
        reviewer.get_widget_specs.return_value = specs
        reviewer.get_value.side_effect = lambda c: {
            "extraction_phrases": [],
            "grounds_payload": [],
        }.get(c, "")
        response = client.post("/populate/_classify")
        assert response.status_code == 200
        reviewer.run_populate.assert_not_called()
        assert "No points to classify" in response.text


class TestPostPopulateAll:
    def _listing_reviewer(self):
        reviewer = _build_mock_reviewer()
        btn = {
            "type": "PopulateButton",
            "field": "_segment",
            "args": {
                "description": "Segment document",
                "target": "units",
                "compute": {"field": "units", "function": "document_segment"},
            },
        }
        reviewer.get_widget_specs.return_value = [btn]
        reviewer.get_review_specs.return_value = [btn]
        reviewer.get_display_layout.return_value = "inline_list"
        reviewer.working_indices.return_value = ["a", "b"]
        reviewer.get_filter_specs.return_value = []
        reviewer.get_sort_specs.return_value = []
        reviewer.get_filter_state.return_value = {}
        reviewer.get_display_detail_field.return_value = "units"
        reviewer.get_row_data.return_value = {"Name": "a", "filename": "a.pdf"}
        reviewer.run_populate.return_value = None
        return reviewer

    def test_runs_for_each_working_index(self):
        reviewer = self._listing_reviewer()
        seen = []
        reviewer.set_index.side_effect = lambda idx: seen.append(idx)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 2
        assert seen[:2] == ["a", "b"]
        assert "Segment document 2/2" in response.text
        assert "Save when ready." in response.text
        assert "Segment document all filtered" not in response.text
        assert 'class="inline-listing"' not in response.text

    def test_skip_filled_false_overwrites_filled_rows(self):
        reviewer = self._listing_reviewer()
        btn = reviewer.get_review_specs.return_value[0]
        btn["args"]["skip_filled"] = False
        reviewer.get_value.return_value = "already classified"
        seen = []
        reviewer.set_index.side_effect = lambda idx: seen.append(idx)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 2
        assert seen[:2] == ["a", "b"]
        assert "Segment document 2/2" in response.text

    def test_continues_after_one_failure(self):
        reviewer = self._listing_reviewer()
        current = {"idx": "alice"}
        reviewer.get_index.side_effect = lambda: current["idx"]

        def _set_index(idx):
            current["idx"] = idx

        reviewer.set_index.side_effect = _set_index

        def _run(interface):
            if current["idx"] == "a":
                raise RuntimeError("missing pdf /secret")

        reviewer.run_populate.side_effect = _run
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 2
        assert "missing pdf" not in response.text
        assert "/secret" not in response.text
        assert "Segment document 1/2" in response.text
        assert "1 failed" in response.text
        assert 'hx-trigger="load delay:50ms"' in response.text
        assert 'class="inline-listing"' not in response.text

    def test_all_failures_report_generic_error(self):
        reviewer = self._listing_reviewer()
        reviewer.run_populate.side_effect = RuntimeError("boom")
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert "failed" in response.text.lower()
        assert "boom" not in response.text

    def test_unknown_field_warns(self):
        reviewer = self._listing_reviewer()
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/missing")
        assert response.status_code == 200
        assert "No PopulateButton" in response.text

    def test_missing_compute_spec_warns(self):
        reviewer = self._listing_reviewer()
        btn = {"type": "PopulateButton", "field": "_segment", "args": {}}
        reviewer.get_widget_specs.return_value = [btn]
        reviewer.get_review_specs.return_value = [btn]
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert "no compute spec" in response.text.lower()
        reviewer.run_populate.assert_not_called()

    def test_get_index_failure_still_runs(self):
        reviewer = self._listing_reviewer()
        n = {"calls": 0}

        def _get_index():
            n["calls"] += 1
            if n["calls"] == 1:
                raise RuntimeError("no current index")
            return "alice"

        reviewer.get_index.side_effect = _get_index
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 2

    def test_restore_index_failure_is_swallowed(self):
        reviewer = self._listing_reviewer()
        reviewer.get_index.return_value = "alice"

        def _set_index(idx):
            if idx == "alice":
                raise RuntimeError("restore failed")

        reviewer.set_index.side_effect = _set_index
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 2

    def _rolling_reviewer(self, n=25, batch=10, *, skip_filled=True, prefilled=False):
        reviewer = self._listing_reviewer()
        btn = {
            "type": "PopulateButton",
            "field": "_segment",
            "args": {
                "description": "Segment document",
                "target": "units",
                "batch": batch,
                "skip_filled": skip_filled,
                "compute": {"field": "units", "function": "document_segment"},
            },
        }
        reviewer.get_widget_specs.return_value = [btn]
        reviewer.get_review_specs.return_value = [btn]
        indices = [f"r{i}" for i in range(n)]
        reviewer.working_indices.return_value = indices
        filled = set(indices) if prefilled else set()
        current = {"idx": None}

        def _set_index(idx):
            current["idx"] = idx

        def _get_value(_col):
            return "done" if current["idx"] in filled else ""

        def _run(_spec):
            filled.add(current["idx"])

        reviewer.set_index.side_effect = _set_index
        reviewer.get_value.side_effect = _get_value
        reviewer.run_populate.side_effect = _run
        reviewer._filled = filled
        return reviewer

    def test_batch_of_ten_chains_until_remaining(self):
        reviewer = self._rolling_reviewer(n=25, batch=10)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 10
        assert "Segment document 10/25" in response.text
        assert 'hx-trigger="load delay:50ms"' in response.text
        assert "secret phrase" not in response.text

    def test_pause_stops_chain_without_more_compute(self):
        reviewer = self._rolling_reviewer(n=25, batch=10)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                first = client.post("/populate-all/_segment")
                paused = client.post("/populate-all/_segment/pause")
        assert first.status_code == 200
        assert paused.status_code == 200
        assert reviewer.run_populate.call_count == 10
        assert "Resume" in paused.text
        assert 'hx-trigger="load' not in paused.text
        assert "Segment document 10/25" in paused.text

    def test_resume_skips_filled_and_computes_next_batch(self):
        reviewer = self._rolling_reviewer(n=25, batch=10)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                client.post("/populate-all/_segment")
                client.post("/populate-all/_segment/pause")
                resumed = client.post("/populate-all/_segment")
                last = client.post("/populate-all/_segment")
        assert reviewer.run_populate.call_count == 25
        assert "Segment document 20/25" in resumed.text
        assert 'hx-trigger="load delay:50ms"' in resumed.text
        assert "Segment document 25/25" in last.text
        assert 'hx-trigger="load' not in last.text
        assert "Save when ready." in last.text

    def test_skip_filled_false_overwrites_in_batches(self):
        reviewer = self._rolling_reviewer(
            n=25, batch=10, skip_filled=False, prefilled=True
        )
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                first = client.post("/populate-all/_segment")
                second = client.post("/populate-all/_segment")
                last = client.post("/populate-all/_segment")
        assert reviewer.run_populate.call_count == 25
        assert "Segment document 10/25" in first.text
        assert "Segment document 20/25" in second.text
        assert "Segment document 25/25" in last.text
        assert 'hx-trigger="load' not in last.text

    def test_skip_empty_passes_over_rows_without_points(self):
        reviewer = self._listing_reviewer()
        btn = {
            "type": "PopulateButton",
            "field": "_classify",
            "args": {
                "description": "Classify",
                "target": "grounds_payload",
                "skip_empty": "extraction_phrases",
                "batch": 10,
                "compute": {
                    "field": ["grounds_payload", "grounds"],
                    "function": "llm_classify_grounds",
                },
            },
        }
        reviewer.get_widget_specs.return_value = [btn]
        reviewer.get_review_specs.return_value = [btn]
        indices = ["empty-a", "ready-a", "empty-b", "ready-b", "empty-c"]
        reviewer.working_indices.return_value = indices
        current = {"idx": None}
        phrases = {
            "empty-a": [],
            "ready-a": [{"phrase": "fairness"}],
            "empty-b": [],
            "ready-b": [{"phrase": "trust"}],
            "empty-c": None,
        }

        def _set_index(idx):
            current["idx"] = idx

        def _get_value(col):
            if col == "extraction_phrases":
                return phrases.get(current["idx"])
            return []

        reviewer.set_index.side_effect = _set_index
        reviewer.get_value.side_effect = _get_value
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_classify")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 2
        assert "Classify 5/5" in response.text
        assert "3 complete" in response.text
        assert "2/5 classified" in response.text
        assert 'id="populate-filled-_classify"' in response.text
        assert 'hx-swap-oob="true"' in response.text
        assert 'hx-trigger="load' not in response.text

    def test_skip_empty_all_empty_completes_without_loop(self):
        reviewer = self._listing_reviewer()
        btn = {
            "type": "PopulateButton",
            "field": "_classify",
            "args": {
                "description": "Classify",
                "target": "grounds_payload",
                "skip_empty": "extraction_phrases",
                "batch": 10,
                "compute": {
                    "field": "grounds_payload",
                    "function": "llm_classify_grounds",
                },
            },
        }
        reviewer.get_widget_specs.return_value = [btn]
        reviewer.get_review_specs.return_value = [btn]
        reviewer.working_indices.return_value = [f"e{i}" for i in range(15)]
        reviewer.get_value.return_value = []
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_classify")
        assert response.status_code == 200
        reviewer.run_populate.assert_not_called()
        assert "Classify 15/15" in response.text
        assert "0/15 classified" in response.text
        assert 'hx-trigger="load' not in response.text

    def test_batch_zero_unbounded_this_request(self):
        reviewer = self._rolling_reviewer(n=5, batch=0)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert reviewer.run_populate.call_count == 5
        assert "Segment document 5/5" in response.text
        assert 'hx-trigger="load' not in response.text

    def test_invalid_and_negative_batch_default_to_ten(self):
        reviewer = self._rolling_reviewer(n=12, batch="nope")
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert reviewer.run_populate.call_count == 10
        assert "12" in response.text
        reviewer.run_populate.reset_mock()
        reviewer = self._rolling_reviewer(n=12, batch=-3)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                client.post("/populate-all/_segment")
        assert reviewer.run_populate.call_count == 10

    def test_working_indices_failure_falls_back_to_index_list(self):
        reviewer = self._listing_reviewer()
        reviewer.working_indices.side_effect = RuntimeError("no working set")
        reviewer.index_list.return_value = ["alice"]
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 1
        reviewer.set_index.assert_any_call("alice")

    def test_get_value_error_treats_row_as_unfilled(self):
        reviewer = self._listing_reviewer()
        reviewer.get_value.side_effect = RuntimeError("missing column")
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert reviewer.run_populate.call_count == 2

    def test_empty_list_and_nan_count_as_unfilled(self):
        reviewer = self._listing_reviewer()
        reviewer.working_indices.return_value = ["a", "b"]
        current = {"idx": None}

        def _set_index(idx):
            current["idx"] = idx

        def _get_value(_col):
            return [] if current["idx"] == "a" else float("nan")

        reviewer.set_index.side_effect = _set_index
        reviewer.get_value.side_effect = _get_value
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert reviewer.run_populate.call_count == 2
        assert "2/2" in response.text

    def test_pause_without_prior_progress_uses_working_total(self):
        reviewer = self._listing_reviewer()
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                paused = client.post("/populate-all/_segment/pause")
        assert paused.status_code == 200
        reviewer.run_populate.assert_not_called()
        assert "Resume" in paused.text
        assert "0/2" in paused.text

    def test_flush_failure_still_returns_chip(self):
        reviewer = self._listing_reviewer()
        reviewer.save_flows.side_effect = OSError("disk full")
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert "populate-progress" in response.text
        assert "disk full" not in response.text

    def test_flush_skipped_when_save_flows_missing(self):
        reviewer = self._listing_reviewer()
        reviewer.save_flows = None
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert "2/2" in response.text

    def test_description_is_escaped_in_chip(self):
        reviewer = self._listing_reviewer()
        btn = reviewer.get_widget_specs.return_value[0]
        btn["args"]["description"] = '<img alt="x" onerror="alert(1)">'
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/populate-all/_segment")
        assert response.status_code == 200
        assert "<img" not in response.text
        assert "<script" not in response.text
        assert "&lt;img" in response.text or "&amp;lt;img" in response.text


class TestPopulateAllHelpers:
    def test_batch_size_empty_and_non_int(self):
        from referia.web.routes import _populate_batch_size

        assert _populate_batch_size({}) == 10
        assert _populate_batch_size({"args": {}}) == 10
        assert _populate_batch_size({"args": {"batch": ""}}) == 10
        assert _populate_batch_size({"args": {"batch": None}}) == 10
        assert _populate_batch_size({"args": {"batch": "x"}}) == 10
        assert _populate_batch_size({"args": {"batch": -1}}) == 10
        assert _populate_batch_size({"args": {"batch": 0}}) == 0
        assert _populate_batch_size({"args": {"batch": 3}}) == 3

    def test_value_is_filled_edges(self):
        from referia.web.routes import _value_is_filled

        assert _value_is_filled(None) is False
        assert _value_is_filled(float("nan")) is False
        assert _value_is_filled("  ") is False
        assert _value_is_filled("") is False
        assert _value_is_filled([]) is False
        assert _value_is_filled({}) is False
        assert _value_is_filled(()) is False
        assert _value_is_filled("done") is True
        assert _value_is_filled(0) is True
        assert _value_is_filled(["x"]) is True

    def test_paused_store_setattr_failures_are_swallowed(self):
        from referia.web.routes import (
            _flush_after_populate_batch,
            _populate_paused_fields,
            _populate_progress,
            _remember_populate_progress,
            _set_populate_paused,
        )

        class BlockSet:
            def __setattr__(self, name, value):
                raise RuntimeError("blocked")

        blocked = BlockSet()
        fields = _populate_paused_fields(blocked)
        assert fields == set()
        _set_populate_paused(blocked, "_extract", True)
        assert _populate_progress(blocked) == {}
        _remember_populate_progress(blocked, "_extract", {"n_ok": 1})

        class Bag:
            pass

        bag = Bag()
        bag._populate_paused_fields = ["not-a-set"]
        assert _populate_paused_fields(bag) == set()
        bag._populate_progress = ["not-a-dict"]
        assert _populate_progress(bag) == {}
        _flush_after_populate_batch(Bag())

        class Flusher:
            def save_flows(self):
                raise OSError("disk")

        _flush_after_populate_batch(Flusher())

    def test_count_filled_target_reads_cache_partition(self):
        import pandas as pd

        from referia.web.routes import _count_filled_target, _populate_filled_counts

        class Data:
            def __init__(self):
                self._d = {
                    "cache": pd.DataFrame(
                        {
                            "grounds_payload": [
                                [{"basis": "principle"}],
                                None,
                                [],
                                {"ok": True},
                            ]
                        },
                        index=["a", "b", "c", "d"],
                    )
                }

        class Reviewer:
            _data = Data()

        reviewer = Reviewer()
        assert _count_filled_target(
            reviewer, "grounds_payload", ["a", "b", "c", "d"]
        ) == 2
        assert _count_filled_target(reviewer, "missing", ["a"]) is None
        specs = [
            {
                "type": "PopulateButton",
                "field": "_classify",
                "args": {"target": "grounds_payload"},
            }
        ]
        assert _populate_filled_counts(reviewer, specs, ["a", "b", "c", "d"]) == {
            "_classify": 2
        }


# ---------------------------------------------------------------------------
# POST /generate-document/{n} and /edit-pdf/{n}
# ---------------------------------------------------------------------------


@pytest.fixture
def document_client():
    """TestClient with generate_document / ensure_edit_pdf mocked."""
    reviewer = _build_mock_reviewer()
    reviewer.list_document_entries.side_effect = lambda section="documents": (
        [{"n": 0, "type": "docx", "label": "Create docx", "summary": False, "section": "documents"}]
        if section == "documents"
        else []
    )
    reviewer.generate_document.return_value = {
        "type": "docx",
        "path": "/tmp/out.docx",
        "href": "/document/out.docx",
        "status": "created",
    }
    reviewer.ensure_edit_pdf.return_value = MagicMock()
    reviewer.document_download_href.return_value = "/document/prepared.pdf"

    with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
        app = create_app(user_file="_referia.yml", directory="/tmp")
        with TestClient(app) as c:
            yield c, reviewer


class TestPostGenerateDocument:
    def test_returns_download_link(self, document_client):
        client, reviewer = document_client
        response = client.post("/generate-document/0")
        assert response.status_code == 200
        reviewer.generate_document.assert_called_once_with(0, summary=False)
        assert "Download" in response.text
        assert 'href="/document/out.docx"' in response.text
        assert 'data-auto-download="/document/out.docx"' in response.text

    def test_summary_route_sets_flag(self, document_client):
        client, reviewer = document_client
        client.post("/generate-summary-document/0")
        reviewer.generate_document.assert_called_once_with(0, summary=True)

    def test_missing_index_warns(self, document_client):
        client, reviewer = document_client
        reviewer.generate_document.side_effect = IndexError("missing")
        response = client.post("/generate-document/9")
        assert response.status_code == 200
        assert "No document" in response.text

    def test_failure_omits_exception_text(self, document_client):
        client, reviewer = document_client
        reviewer.generate_document.side_effect = RuntimeError("secret path /tmp/x")
        response = client.post("/generate-document/0")
        assert response.status_code == 200
        assert "failed" in response.text.lower()
        assert "secret path" not in response.text

    def test_panel_shows_document_button_in_nav(self, document_client):
        client, _ = document_client
        response = client.get("/")
        assert response.status_code == 200
        assert 'hx-post="/generate-document/0"' in response.text
        assert "nav-document-actions" in response.text
        assert "nav-actions" in response.text
        # Create buttons live in nav chrome, not the Documents panel body
        doc_panel_start = response.text.find('class="document-panel"')
        if doc_panel_start != -1:
            assert 'hx-post="/generate-document/0"' not in response.text[doc_panel_start:]

    def test_generate_honours_form_index(self, document_client):
        client, reviewer = document_client
        response = client.post("/generate-document/0", data={"index": "bob"})
        assert response.status_code == 200
        reviewer.set_index.assert_called_with("bob")
        reviewer.generate_document.assert_called_once_with(0, summary=False)

    def test_generate_ignores_empty_form_index(self, document_client):
        client, reviewer = document_client
        reviewer.set_index.reset_mock()
        response = client.post("/generate-document/0", data={"index": ""})
        assert response.status_code == 200
        reviewer.set_index.assert_not_called()
        reviewer.generate_document.assert_called_once_with(0, summary=False)

    def test_generate_reports_invalid_form_index(self, document_client):
        client, reviewer = document_client
        reviewer.set_index.side_effect = KeyError("ghost")
        reviewer.generate_document.reset_mock()
        response = client.post("/generate-document/0", data={"index": "ghost"})
        assert response.status_code == 200
        assert "Generate document failed" in response.text
        assert "See server log" in response.text
        reviewer.generate_document.assert_not_called()


class TestPostEditPdf:
    def test_returns_download_link(self, document_client):
        client, reviewer = document_client
        response = client.post("/edit-pdf/0")
        assert response.status_code == 200
        reviewer.ensure_edit_pdf.assert_called_once_with(0)
        assert "Download" in response.text
        assert 'href="/document/prepared.pdf"' in response.text
        assert 'data-auto-download="/document/prepared.pdf"' in response.text

    def test_failure_omits_exception_text(self, document_client):
        client, reviewer = document_client
        reviewer.ensure_edit_pdf.side_effect = RuntimeError("internal pdf boom")
        response = client.post("/edit-pdf/0")
        assert response.status_code == 200
        assert "failed" in response.text.lower()
        assert "internal pdf boom" not in response.text


# ---------------------------------------------------------------------------
# visible_if: fields must come from the full row, not just widget fields
# ---------------------------------------------------------------------------


class TestCurrentDataIncludesVisibleIfFields:
    """Regression tests for the bug where columns used in visible_if conditions
    were absent from the data dict passed to render_form, causing conditional
    sections to be permanently hidden in the web interface.

    Before the fix, _current_data() only read values for fields that had
    associated widgets.  Columns like "abstractPresent" used only in
    visible_if conditions were missing, so data.get("abstractPresent")
    returned None and every conditional section was hidden.

    After the fix, _current_data() starts from reviewer.get_row_data() which
    returns ALL columns for the current record.
    """

    def test_visible_if_field_included_in_rendered_html(self, mock_reviewer, client):
        """A widget with visible_if should be VISIBLE when the flag column is True."""
        mock_reviewer.get_review_specs.return_value = [
            {
                "type": "Textarea",
                "field": "abstractText",
                "args": {"description": "Abstract"},
                "visible_if": "abstractPresent",
            }
        ]
        mock_reviewer.get_widget_specs.return_value = [
            {
                "type": "Textarea",
                "field": "abstractText",
                "args": {"description": "Abstract"},
                "visible_if": "abstractPresent",
            }
        ]
        # get_row_data returns ALL columns including the non-widget flag
        mock_reviewer.get_row_data.return_value = {
            "abstractText": "Some abstract text",
            "abstractPresent": True,  # flag column — no corresponding widget
        }
        mock_reviewer.get_value.side_effect = lambda col: (
            "Some abstract text" if col == "abstractText" else None
        )

        response = client.get("/")
        assert response.status_code == 200
        # Widget should NOT have display:none (visible because abstractPresent is True)
        assert 'style="display:none"' not in response.text

    def test_visible_if_field_missing_hides_widget(self, mock_reviewer, client):
        """When the flag column is absent from row_data, the widget should be hidden."""
        mock_reviewer.get_review_specs.return_value = [
            {
                "type": "Textarea",
                "field": "forewordText",
                "args": {"description": "Foreword"},
                "visible_if": "forewordPresent",
            }
        ]
        mock_reviewer.get_widget_specs.return_value = [
            {
                "type": "Textarea",
                "field": "forewordText",
                "args": {"description": "Foreword"},
                "visible_if": "forewordPresent",
            }
        ]
        # get_row_data does NOT include forewordPresent (or it is falsy)
        mock_reviewer.get_row_data.return_value = {
            "forewordText": "",
            # forewordPresent absent → defaults to None → widget hidden
        }
        mock_reviewer.get_value.return_value = ""

        response = client.get("/")
        assert response.status_code == 200
        # Widget should have display:none because forewordPresent is missing/falsy
        assert 'style="display:none"' in response.text

    def test_panel_hides_gated_viewer_but_keeps_it_in_dom(
        self, mock_reviewer, client
    ):
        from referia.web.render import render_viewer

        mock_reviewer.get_viewer_specs.return_value = [
            {
                "type": "Section",
                "title": "Chapter 8",
                "inherited": True,
                "visible_if": "ch8Present",
                "entries": [
                    {
                        "type": "Markdown",
                        "liquid": "Chapter 8 notes",
                        "visible_if": "ch8Present",
                    }
                ],
            }
        ]
        mock_reviewer.get_row_data.return_value = {"ch8Present": False}
        mock_reviewer.render_viewer_html.side_effect = (
            lambda spec, viewer_index=0: render_viewer(
                spec,
                "Chapter 8 notes",
                viewer_index=viewer_index,
                data=mock_reviewer.get_row_data(),
            )
        )

        response = client.get("/")
        assert response.status_code == 200
        assert "Chapter 8 notes" in response.text
        assert 'class="review-section viewer-section inherited-section"' in response.text
        assert response.text.count('style="display:none"') >= 2

    def test_field_update_oob_swaps_gated_viewer(self, client, mock_reviewer):
        mock_reviewer.affected_widgets.return_value = set()
        mock_reviewer.get_viewer_specs.return_value = [
            {
                "type": "Markdown",
                "liquid": "Chapter 8 notes",
                "visible_if": "ch8Present",
            }
        ]
        mock_reviewer.render_viewer_html.side_effect = (
            lambda spec, viewer_index=0: (
                f'<div class="viewer viewer-markdown" '
                f'id="viewer-markdown-{viewer_index}" style="display:none">'
                f"Chapter 8 notes</div>"
            )
        )
        response = client.post("/field/ch8Present", data={"ch8Present": "true"})
        assert response.status_code == 200
        assert 'id="viewer-markdown-0"' in response.text
        assert 'hx-swap-oob="true"' in response.text
        assert "Chapter 8 notes" in response.text
        assert "display:none" in response.text

    def test_string_false_hides_visible_if_widget(self, mock_reviewer, client):
        """Soft-fill \"False\" must hide dependents in the full panel render."""
        mock_reviewer.get_review_specs.return_value = [
            {
                "type": "Textarea",
                "field": "Email Comment",
                "args": {"description": "Email Comment"},
                "visible_if": "Interview",
            }
        ]
        mock_reviewer.get_widget_specs.return_value = list(
            mock_reviewer.get_review_specs.return_value
        )
        mock_reviewer.get_row_data.return_value = {
            "Email Comment": "draft",
            "Interview": "False",
        }
        mock_reviewer.get_value.return_value = "draft"

        response = client.get("/")
        assert response.status_code == 200
        assert 'style="display:none"' in response.text

    def test_panel_hides_gated_document_action(self, mock_reviewer, client):
        mock_reviewer.list_document_entries.side_effect = lambda section="documents": (
            [
                {
                    "n": 0,
                    "type": "email",
                    "label": "Create Email",
                    "summary": False,
                    "section": "documents",
                    "visible_if": "Interview",
                }
            ]
            if section == "documents"
            else []
        )
        mock_reviewer.get_row_data.return_value = {"Interview": False}
        response = client.get("/")
        assert response.status_code == 200
        assert 'id="nav-document-actions"' in response.text
        assert "Create Email" not in response.text

    def test_panel_shows_gated_document_action_when_true(self, mock_reviewer, client):
        mock_reviewer.list_document_entries.side_effect = lambda section="documents": (
            [
                {
                    "n": 0,
                    "type": "email",
                    "label": "Create Email",
                    "summary": False,
                    "section": "documents",
                    "visible_if": "Interview",
                }
            ]
            if section == "documents"
            else []
        )
        mock_reviewer.get_row_data.return_value = {"Interview": True}
        response = client.get("/")
        assert response.status_code == 200
        assert "Create Email" in response.text
        assert 'hx-post="/generate-document/0"' in response.text

    def test_inline_list_puts_record_documents_on_rows(
        self, mock_reviewer, client
    ):
        mock_reviewer.get_display_layout.return_value = "inline_list"
        mock_reviewer.working_indices.return_value = ["alice", "bob"]
        mock_reviewer.get_filter_specs.return_value = []
        mock_reviewer.get_sort_specs.return_value = []
        mock_reviewer.get_filter_state.return_value = {}
        mock_reviewer.get_display_detail_field.return_value = None
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "noted", "args": {"description": "Noted"}},
            {"type": "SaveButton"},
        ]
        current = {"idx": "alice"}
        rows = {
            "alice": {"title": "Alice", "markedFlag": "no"},
            "bob": {"title": "Bob", "markedFlag": "yes"},
        }

        def _set_index(idx):
            current["idx"] = idx

        mock_reviewer.get_index.side_effect = lambda: current["idx"]
        mock_reviewer.set_index.side_effect = _set_index
        mock_reviewer.get_row_data.side_effect = lambda: dict(rows[current["idx"]])
        mock_reviewer.list_document_entries.side_effect = (
            lambda section="documents": (
                [
                    {
                        "n": 0,
                        "type": "email",
                        "label": "Email feedback",
                        "summary": False,
                        "section": "documents",
                        "visible_if": {"field": "markedFlag", "equals": True},
                    }
                ]
                if section == "documents"
                else []
            )
        )
        response = client.get("/")
        assert response.status_code == 200
        assert "Email feedback" in response.text
        assert response.text.count("Email feedback") == 1
        assert 'id="row-document-actions-bob"' in response.text
        assert "hx-vals=" in response.text
        # Per-record emails live on rows, not in the nav chrome.
        nav = response.text.split('id="nav-document-actions"', 1)[-1]
        nav = nav.split("</div>", 1)[0]
        assert "Email feedback" not in nav

    def test_inline_list_windows_first_get_and_append_fragment(
        self, mock_reviewer, client
    ):
        ids = [f"r{i}" for i in range(2013)]
        mock_reviewer.get_display_layout.return_value = "inline_list"
        mock_reviewer.working_indices.return_value = ids
        mock_reviewer.get_filter_specs.return_value = []
        mock_reviewer.get_sort_specs.return_value = []
        mock_reviewer.get_filter_state.return_value = {}
        mock_reviewer.get_display_detail_field.return_value = None
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "complete"},
            {
                "type": "PopulateButton",
                "field": "_extract",
                "args": {"description": "Extract", "all": True},
            },
        ]
        mock_reviewer.get_widget_specs.return_value = (
            mock_reviewer.get_review_specs.return_value
        )
        mock_reviewer.get_row_data.side_effect = lambda: {
            "title": str(mock_reviewer.get_index()),
            "complete": False,
        }
        first = client.get("/")
        assert first.status_code == 200
        assert first.text.count('data-index="') == 50
        assert "2013" in first.text
        assert "Extract all" in first.text
        assert 'hx-post="/populate-all/_extract"' in first.text
        assert "Load more" in first.text
        assert 'id="listing-sentinel"' in first.text
        frag = client.get(
            "/listing-page?list_offset=50",
            headers={"HX-Request": "true"},
        )
        assert frag.status_code == 200
        assert "Select all filtered" not in frag.text
        assert "Extract all" not in frag.text
        assert "listing-page-chunk" in frag.text
        assert 'data-index="r50"' in frag.text
        assert 'data-index="r0"' not in frag.text

    def test_inline_list_page_mode_replaces_rows(
        self, mock_reviewer, client
    ):
        ids = [f"r{i}" for i in range(2013)]
        mock_reviewer.get_display_layout.return_value = "inline_list"
        mock_reviewer.working_indices.return_value = ids
        mock_reviewer.get_list_paging.return_value = "page"
        mock_reviewer.get_filter_specs.return_value = []
        mock_reviewer.get_sort_specs.return_value = []
        mock_reviewer.get_filter_state.return_value = {}
        mock_reviewer.get_display_detail_field.return_value = None
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "complete"}
        ]
        mock_reviewer.get_widget_specs.return_value = (
            mock_reviewer.get_review_specs.return_value
        )
        mock_reviewer.get_row_data.side_effect = lambda: {
            "title": str(mock_reviewer.get_index()),
            "complete": False,
        }
        first = client.get("/?list_page_size=25&list_page=1")
        assert first.status_code == 200
        assert first.text.count('data-index="') == 25
        assert "Page 1 of 81" in first.text
        assert "Load more" not in first.text
        page2 = client.get("/listing-page?list_page_size=25&list_page=2")
        assert "Page 2 of 81" in page2.text
        assert 'data-index="r25"' in page2.text
        assert 'data-index="r0"' not in page2.text
        assert page2.text.count('data-index="') == 25

    def test_inline_list_unbounded_walks_all(self, mock_reviewer, client):
        ids = [f"r{i}" for i in range(20)]
        mock_reviewer.get_display_layout.return_value = "inline_list"
        mock_reviewer.working_indices.return_value = ids
        mock_reviewer.get_filter_specs.return_value = []
        mock_reviewer.get_sort_specs.return_value = []
        mock_reviewer.get_filter_state.return_value = {}
        mock_reviewer.get_display_detail_field.return_value = None
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "complete"}
        ]
        mock_reviewer.get_widget_specs.return_value = (
            mock_reviewer.get_review_specs.return_value
        )
        mock_reviewer.get_row_data.side_effect = lambda: {
            "title": str(mock_reviewer.get_index()),
            "complete": False,
        }
        response = client.get("/?list_page_size=0")
        assert response.status_code == 200
        assert response.text.count('data-index="') == 20
        assert "Load more" not in response.text
        assert "listing-pager" not in response.text

    def test_filter_post_resets_to_first_page(self, mock_reviewer, client):
        ids = [f"r{i}" for i in range(80)]
        mock_reviewer.get_display_layout.return_value = "inline_list"
        mock_reviewer.working_indices.return_value = ids
        mock_reviewer.get_filter_specs.return_value = []
        mock_reviewer.get_sort_specs.return_value = []
        mock_reviewer.get_filter_state.return_value = {}
        mock_reviewer.get_display_detail_field.return_value = None
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "complete"}
        ]
        mock_reviewer.get_widget_specs.return_value = (
            mock_reviewer.get_review_specs.return_value
        )
        mock_reviewer.get_row_data.side_effect = lambda: {
            "title": str(mock_reviewer.get_index()),
            "complete": False,
        }
        later = client.get("/?list_offset=50")
        assert 'data-index="r50"' in later.text
        reset = client.post("/filters")
        assert reset.status_code == 200
        assert 'data-index="r0"' in reset.text
        assert 'data-index="r50"' not in reset.text

    def test_listing_page_empty_when_not_inline_list(self, mock_reviewer, client):
        mock_reviewer.get_display_layout.return_value = "side_by_side"
        response = client.get("/listing-page?list_offset=50")
        assert response.status_code == 200
        assert response.text == ""

    def test_listing_page_empty_when_layout_raises(self, mock_reviewer, client):
        mock_reviewer.get_display_layout.side_effect = RuntimeError("layout boom")
        response = client.get("/listing-page")
        assert response.status_code == 200
        assert response.text == ""

    def test_listing_page_invalid_query_fails_closed(self, mock_reviewer, client):
        ids = [f"r{i}" for i in range(8)]
        mock_reviewer.get_display_layout.return_value = "inline_list"
        mock_reviewer.working_indices.return_value = ids
        mock_reviewer.get_filter_specs.return_value = []
        mock_reviewer.get_sort_specs.return_value = []
        mock_reviewer.get_filter_state.return_value = {}
        mock_reviewer.get_display_detail_field.return_value = None
        mock_reviewer.get_review_specs.return_value = [
            {"type": "Checkbox", "field": "complete"}
        ]
        mock_reviewer.get_row_data.side_effect = lambda: {
            "title": str(mock_reviewer.get_index()),
            "complete": False,
        }
        response = client.get(
            "/listing-page?list_offset=-9&list_page=abc&list_page_size=-2"
        )
        assert response.status_code == 200
        assert 'data-index="r0"' in response.text

    def test_window_helpers_cover_webreviewer_and_restore_edges(self, mock_reviewer):
        from referia.assess.web_review import WebReviewer
        from referia.web.routes import (
            _collect_listing_entries,
            _parse_list_query,
            _window_for_reviewer,
        )

        assert _parse_list_query(None)["offset"] == 0
        req = MagicMock()
        req.query_params.get.side_effect = lambda name: {
            "list_page": "",
            "list_offset": "-3",
            "list_page_size": "bad",
        }.get(name)
        parsed = _parse_list_query(req)
        assert parsed["page"] is None
        assert parsed["offset"] == 0
        assert parsed["page_size"] is None

        spec = MagicMock(spec=WebReviewer)
        spec.working_indices.side_effect = RuntimeError("no working")
        spec.index_list.return_value = ["a", "b"]
        spec.get_list_page_size.return_value = 50
        spec.get_list_paging.return_value = "append"
        spec.list_query.return_value = {
            "offset": 0,
            "page": None,
            "page_size": None,
        }
        window = _window_for_reviewer(spec)
        spec.list_query.assert_called()
        assert window["page_indices"] == ["a", "b"]
        _window_for_reviewer(spec, reset=True)
        spec.clear_list_window.assert_called()
        remember_req = MagicMock()
        remember_req.query_params.get.side_effect = lambda name: {
            "list_offset": "50",
            "list_page": None,
            "list_page_size": "25",
        }.get(name)
        spec.working_indices.side_effect = None
        spec.working_indices.return_value = [f"r{i}" for i in range(80)]
        spec.get_list_page_size.side_effect = lambda override=None: (
            25 if override is not None else 50
        )
        _window_for_reviewer(spec, remember_req)
        spec.remember_list_query.assert_called()

        mock_reviewer.get_list_paging.return_value = "scroll"
        mock_reviewer.working_indices.return_value = ["x"]
        other = _window_for_reviewer(mock_reviewer, remember_req)
        assert other["paging"] == "append"
        mock_reviewer.get_list_paging.return_value = "page"
        paged = _window_for_reviewer(mock_reviewer, remember_req)
        assert paged["paging"] == "page"

        mock_reviewer.get_index.side_effect = RuntimeError("no current")
        mock_reviewer.get_row_data.return_value = {}
        mock_reviewer.get_filter_state.return_value = {}
        rows = _collect_listing_entries(mock_reviewer, ["bob"], "")
        assert rows[0]["index"] == "bob"

        mock_reviewer.get_index.side_effect = None
        mock_reviewer.get_index.return_value = "alice"

        def _set_index(idx):
            if idx == "alice":
                raise RuntimeError("restore failed")

        mock_reviewer.set_index.side_effect = _set_index
        restored = _collect_listing_entries(mock_reviewer, ["bob"], "")
        assert restored[0]["index"] == "bob"

    def test_inline_list_field_update_oob_omits_record_documents(
        self, mock_reviewer, client
    ):
        mock_reviewer.get_display_layout.return_value = "inline_list"
        mock_reviewer.list_document_entries.side_effect = (
            lambda section="documents": (
                [
                    {
                        "n": 0,
                        "type": "email",
                        "label": "Email feedback",
                        "summary": False,
                        "section": "documents",
                    }
                ]
                if section == "documents"
                else [
                    {
                        "n": 0,
                        "type": "xlsx",
                        "label": "Export scores",
                        "summary": True,
                        "section": "summary_documents",
                    }
                ]
            )
        )
        mock_reviewer.get_row_data.return_value = {"noted": True}
        mock_reviewer.affected_widgets.return_value = set()
        response = client.post("/field/noted", data={"noted": "true"})
        assert response.status_code == 200
        assert "Export scores" in response.text
        assert "Email feedback" not in response.text
        assert 'hx-swap-oob="true"' in response.text


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_ok_when_reviewer_loaded(self, client):
        data = response = client.get("/health").json()
        assert data["status"] == "ok"
        assert data["reviewer"] == "loaded"


class TestDocumentRoutes:
    def test_document_serves_file_under_review_dir(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")
        reviewer = _build_mock_reviewer()
        reviewer._directory = str(tmp_path)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory=str(tmp_path))
            with TestClient(app) as c:
                response = c.get("/document/paper.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.content.startswith(b"%PDF")

    def test_document_rejects_traversal(self, tmp_path):
        reviewer = _build_mock_reviewer()
        reviewer._directory = str(tmp_path)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory=str(tmp_path))
            with TestClient(app) as c:
                response = c.get("/document/%2e%2e/secret.pdf")
        assert response.status_code in {403, 404}
        assert not response.content.startswith(b"%PDF")

    def test_record_document_serves_resolved_pdf(self, tmp_path):
        pdf = tmp_path / "thesis.pdf"
        pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")
        reviewer = _build_mock_reviewer()
        reviewer._directory = str(tmp_path)
        reviewer.get_record_document.return_value = pdf
        reviewer.allowed_roots_for_document.return_value = [tmp_path]
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory=str(tmp_path))
            with TestClient(app) as c:
                response = c.get(
                    "/record-document/localpdf/0", params={"index": "alice"}
                )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")
        reviewer.set_index.assert_called_with("alice")

    def test_record_document_applies_index_before_resolve(self, tmp_path):
        pdf = tmp_path / "thesis.pdf"
        pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")
        reviewer = _build_mock_reviewer()
        reviewer._directory = str(tmp_path)
        reviewer.get_record_document.return_value = pdf
        reviewer.allowed_roots_for_document.return_value = [tmp_path]
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory=str(tmp_path))
            with TestClient(app) as c:
                response = c.get(
                    "/record-document/editpdf/0", params={"index": "bob"}
                )
        assert response.status_code == 200
        reviewer.set_index.assert_called_once_with("bob")

    def test_record_document_missing_index_404(self, tmp_path):
        reviewer = _build_mock_reviewer()
        reviewer._directory = str(tmp_path)
        reviewer.set_index.side_effect = KeyError('Index "99" not found in data')
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory=str(tmp_path))
            with TestClient(app) as c:
                response = c.get(
                    "/record-document/localpdf/0", params={"index": "99"}
                )
        assert response.status_code == 404

    def test_record_document_unknown_kind_404(self, client):
        response = client.get("/record-document/nope/0")
        assert response.status_code == 404

    def test_page_includes_pdf_iframe_when_present(self, tmp_path):
        reviewer = _build_mock_reviewer()
        reviewer._directory = str(tmp_path)
        reviewer.list_pdf_entries.return_value = [
            {"kind": "localpdf", "n": 0, "label": "thesis", "exists": True},
        ]
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory=str(tmp_path))
            with TestClient(app) as c:
                response = c.get("/")
        assert "document-panel" in response.text
        assert 'src="/record-document/localpdf/0?index=alice"' in response.text
        assert "thesis" in response.text

    def test_page_includes_resizable_column_splitter(self, client):
        response = client.get("/")
        assert 'class="two-col"' in response.text
        assert 'class="col-splitter"' in response.text
        assert 'role="separator"' in response.text
        assert "referia.split.viewerPct" in response.text

    def test_page_persists_document_details_open_state(self, tmp_path):
        reviewer = _build_mock_reviewer()
        reviewer._directory = str(tmp_path)
        reviewer.list_pdf_entries.return_value = [
            {"kind": "editpdf", "n": 0, "label": "proposal", "exists": True},
        ]
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory=str(tmp_path))
            with TestClient(app) as c:
                response = c.get("/")
        assert 'data-doc-key="editpdf/0"' in response.text
        assert "referia.pdfEntry.open" in response.text


class TestListingChromeHelpers:
    def test_liquid_viewer_watch_columns(self):
        from referia.web.routes import _liquid_viewer_watch_columns

        assert _liquid_viewer_watch_columns({"field": "units"}) == {"units"}
        assert _liquid_viewer_watch_columns({"field": "_", "watch": "units"}) == {"units"}
        assert _liquid_viewer_watch_columns(
            {"watch": ["units", "_", None, ""]}
        ) == {"units"}
        assert _liquid_viewer_watch_columns({"field": None}) == set()

    def test_apply_field_bulk_writes_parameter_once(self):
        from referia.web.routes import _apply_field_bulk

        reviewer = MagicMock()
        data = MagicMock()
        data.isparameter.return_value = True
        data.ismutable.return_value = True
        reviewer._data = data
        _apply_field_bulk(reviewer, "phrase_kinds", "a, b")
        reviewer.set_value.assert_called_once_with("phrase_kinds", "a, b")
        reviewer.working_indices.assert_not_called()

    def test_apply_field_bulk_falls_back_when_parameter_probe_fails(self):
        from referia.web.routes import _apply_field_bulk

        reviewer = MagicMock()
        data = MagicMock()
        data.isparameter.side_effect = RuntimeError("no store")
        data.ismutable.return_value = True
        reviewer._data = data
        reviewer.get_index.return_value = "alice"
        reviewer.working_indices.return_value = ["a", "b"]
        _apply_field_bulk(reviewer, "complete", True)
        assert reviewer.set_value.call_count == 2
        reviewer.set_index.assert_any_call("alice")

    def test_apply_field_bulk_swallows_get_and_restore_index_errors(self):
        from referia.web.routes import _apply_field_bulk

        reviewer = MagicMock()
        reviewer._data = None
        reviewer.get_index.side_effect = RuntimeError("no index")
        reviewer.working_indices.return_value = ["a"]
        _apply_field_bulk(reviewer, "complete", True)
        reviewer.set_value.assert_called_once_with("complete", True)

        reviewer = MagicMock()
        reviewer._data = None
        reviewer.get_index.return_value = "alice"
        reviewer.working_indices.return_value = ["a"]

        def _set_index(idx):
            if idx == "alice":
                raise RuntimeError("cannot restore")

        reviewer.set_index.side_effect = _set_index
        _apply_field_bulk(reviewer, "complete", True)
        reviewer.set_value.assert_called_once_with("complete", True)

    def test_field_bulk_error_returns_oob_status(self):
        reviewer = _build_mock_reviewer()
        n = {"calls": 0}

        def _working_indices():
            n["calls"] += 1
            if n["calls"] == 1:
                raise RuntimeError("bulk boom")
            return []

        reviewer.working_indices.side_effect = _working_indices
        reviewer.get_display_layout.return_value = "inline_list"
        reviewer.get_filter_specs.return_value = []
        reviewer.get_sort_specs.return_value = []
        reviewer.get_filter_state.return_value = {}
        reviewer.get_display_detail_field.return_value = None
        spec = {"type": "Checkbox", "field": "complete"}
        reviewer.get_review_specs.return_value = [spec]
        reviewer.get_widget_specs.return_value = [spec]
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                response = client.post("/field-bulk/complete", data={"complete": "true"})
        assert response.status_code == 200
        assert "Bulk update failed" in response.text
        assert "bulk boom" not in response.text
        assert 'hx-swap-oob="true"' in response.text

    def test_populate_without_compute_spec_warns(self, populate_client):
        client, reviewer = populate_client
        reviewer.get_widget_specs.return_value = [
            {"type": "PopulateButton", "field": "SummaryBtn", "args": {}},
        ]
        response = client.post("/populate/SummaryBtn")
        assert response.status_code == 200
        assert "no compute spec" in response.text.lower()
        reviewer.run_populate.assert_not_called()
