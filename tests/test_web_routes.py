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

    def test_save_button_includes_form_values(self, client):
        """Save button must carry hx-include so widget state is captured on click."""
        response = client.get("/")
        assert 'hx-include="#review-form"' in response.text

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

    def test_save_applies_form_values_before_saving(self, client, mock_reviewer):
        """The save route must call set_value for each form field before save_flows.

        This is the regression test for the bug where the Save button posted
        no form data, so slider / textarea changes were never persisted even
        though the user had edited them.
        """
        client.post("/save", data={"Comment": "looks good", "Score": "7"})
        calls = {call.args[0]: call.args[1] for call in mock_reviewer.set_value.call_args_list}
        assert "Comment" in calls
        assert calls["Comment"] == "looks good"
        assert "Score" in calls
        # IntSlider fields must arrive as int, not str
        assert calls["Score"] == 7
        assert isinstance(calls["Score"], int)

    def test_save_applies_int_slider_as_integer(self, client, mock_reviewer):
        """HTML forms always send strings; IntSlider values must be coerced to int."""
        client.post("/save", data={"Score": "3"})
        score_call = next(
            (c for c in mock_reviewer.set_value.call_args_list if c.args[0] == "Score"),
            None,
        )
        assert score_call is not None
        assert score_call.args[1] == 3
        assert isinstance(score_call.args[1], int)

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


class TestPostPopulate:
    def test_returns_200(self, client):
        response = client.post("/populate/Comment")
        assert response.status_code == 200

    def test_response_acknowledges_field(self, client):
        response = client.post("/populate/Comment")
        # Should return the current widget value at minimum
        assert "widget-Comment" in response.text or "Populate" in response.text


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
