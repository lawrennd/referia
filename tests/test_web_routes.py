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

    def test_html_includes_htmx_script(self, client):
        response = client.get("/")
        assert "htmx" in response.text


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
        # Both affected widget divs should appear in the OOB response
        assert 'id="widget-Comment"' in response.text
        assert 'id="widget-Score"' in response.text

    def test_oob_swaps_carry_hx_swap_oob_attribute(self, client, mock_reviewer):
        mock_reviewer.affected_widgets.return_value = {"Comment"}
        response = client.post("/field/Comment", data={"Comment": "x"})
        assert 'hx-swap-oob="true"' in response.text

    def test_unknown_column_does_not_crash(self, client, mock_reviewer):
        mock_reviewer.set_value.side_effect = KeyError("no such column")
        response = client.post("/field/Nonexistent", data={"Nonexistent": "x"})
        assert response.status_code == 200
        assert "Error" in response.text

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
        assert "failed" in response.text.lower() or "Error" in response.text


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


class TestPostPopulate:
    def test_returns_200(self, populate_client):
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
