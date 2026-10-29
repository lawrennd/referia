"""Unit tests for referia.web.render — widget-to-HTML renderer.

Covers render_widget() for every supported widget type, render_viewer(),
render_form(), visible_if conditions, and HTML escaping.
"""

import logging
import math

import pytest
from referia.web.render import (
    _combine_html_styles,
    _evaluate_liquid,
    _liquid_environment,
    _markdown_widget_content,
    render_form,
    render_viewer,
    render_widget,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _w(type_, field="col", args=None, **extra):
    """Minimal widget spec factory."""
    spec = {"type": type_, "field": field, "args": args or {}}
    spec.update(extra)
    return spec


# ---------------------------------------------------------------------------
# Container wrapping
# ---------------------------------------------------------------------------

class TestWidgetContainer:
    def test_container_div_present(self):
        html = render_widget(_w("Text", "name"), "Alice")
        assert 'class="widget-container"' in html

    def test_container_id_uses_field(self):
        html = render_widget(_w("Text", "my_field"), "v")
        assert 'id="widget-my_field"' in html

    def test_no_id_when_field_empty(self):
        html = render_widget({"type": "SaveButton", "field": "", "args": {}})
        assert "id=" not in html

    def test_populate_button_uses_btn_prefix_not_widget_prefix(self):
        """PopulateButton must not collide with its target field's widget-{field} id."""
        html = render_widget(
            {"type": "PopulateButton", "field": "summary", "args": {"description": "Go"}},
            None,
        )
        assert 'id="btn-widget-summary"' in html
        assert 'id="widget-summary"' not in html

    def test_container_id_sanitises_spaces(self):
        """Spaced field names must become CSS-safe ids (HTMX OOB uses querySelector)."""
        html = render_widget(_w("Textarea", "Importance Fairness"), "")
        assert 'id="widget-Importance_Fairness"' in html
        assert 'id="widget-Importance Fairness"' not in html

    def test_unsafe_field_name_logs_once(self, caplog):
        """Sanitising a field name should warn once, not on every render."""
        import logging
        from referia.web import render as render_mod

        render_mod._warned_dom_ids.discard("Overall Fairness")
        with caplog.at_level(logging.WARNING, logger="referia.web.render"):
            render_widget(_w("Textarea", "Overall Fairness"), "")
            render_widget(_w("Textarea", "Overall Fairness"), "")
        matches = [r for r in caplog.records if "Overall Fairness" in r.getMessage()]
        assert len(matches) == 1
        assert "rewritten" in matches[0].getMessage()


# ---------------------------------------------------------------------------
# Textarea
# ---------------------------------------------------------------------------

class TestTextarea:
    def test_element_present(self):
        html = render_widget(_w("Textarea", "notes"), "hello")
        assert "<textarea" in html
        assert "hello" in html

    def test_htmx_post(self):
        html = render_widget(_w("Textarea", "notes"), "")
        assert 'hx-post="/field/notes"' in html

    def test_htmx_trigger_includes_blur(self):
        """Textarea must fire on blur so typing → immediate Save click is captured."""
        html = render_widget(_w("Textarea", "notes"), "")
        assert "blur" in html

    def test_rows_default(self):
        html = render_widget(_w("Textarea", "notes"), "")
        assert 'rows="5"' in html

    def test_rows_custom(self):
        html = render_widget(_w("Textarea", "notes", args={"rows": 10}), "")
        assert 'rows="10"' in html

    def test_description_label(self):
        html = render_widget(_w("Textarea", "notes", args={"description": "My notes"}), "")
        assert "My notes" in html

    def test_value_escaped(self):
        html = render_widget(_w("Textarea", "x"), "<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

class TestText:
    def test_input_type_text(self):
        html = render_widget(_w("Text", "name"), "Alice")
        assert 'type="text"' in html

    def test_value_attribute(self):
        html = render_widget(_w("Text", "name"), "Alice")
        assert 'value="Alice"' in html

    def test_htmx_post(self):
        html = render_widget(_w("Text", "name"), "")
        assert 'hx-post="/field/name"' in html

    def test_htmx_trigger_includes_blur(self):
        """Text input must fire on blur so typing → immediate Save click is captured."""
        html = render_widget(_w("Text", "name"), "")
        assert "blur" in html

    def test_value_escaped(self):
        html = render_widget(_w("Text", "x"), '"quoted"')
        assert '"quoted"' not in html
        assert "&quot;quoted&quot;" in html


# ---------------------------------------------------------------------------
# IntSlider / FloatSlider
# ---------------------------------------------------------------------------

class TestSliders:
    def test_int_slider_type_range(self):
        html = render_widget(_w("IntSlider", "score", args={"min": 0, "max": 10}), 5)
        assert 'type="range"' in html
        assert 'min="0"' in html
        assert 'max="10"' in html
        assert 'value="5"' in html

    def test_int_slider_output_element(self):
        html = render_widget(_w("IntSlider", "score"), 3)
        assert "<output" in html

    def test_float_slider(self):
        html = render_widget(_w("FloatSlider", "ratio", args={"min": 0.0, "max": 1.0, "step": 0.1}), 0.5)
        assert 'type="range"' in html
        assert 'step="0.1"' in html

    def test_slider_trigger_includes_mouseup(self):
        """Sliders must fire on mouseup so drag → release is captured even when
        the `change` event has not fired yet (common in Chrome/Safari)."""
        html = render_widget(_w("IntSlider", "score"), 5)
        assert "mouseup" in html

    def test_float_slider_trigger_includes_mouseup(self):
        html = render_widget(_w("FloatSlider", "ratio"), 0.5)
        assert "mouseup" in html


# ---------------------------------------------------------------------------
# IntText / BoundedIntText / BoundedFloatText
# ---------------------------------------------------------------------------

class TestNumberInputs:
    def test_int_text(self):
        html = render_widget(_w("IntText", "count"), 42)
        assert 'type="number"' in html
        assert 'value="42"' in html
        assert 'step="1"' in html

    def test_bounded_int_text_with_bounds(self):
        html = render_widget(_w("BoundedIntText", "score", args={"min": 1, "max": 10}), 5)
        assert 'min="1"' in html
        assert 'max="10"' in html

    def test_bounded_float_text(self):
        html = render_widget(_w("BoundedFloatText", "rate", args={"step": 0.5}), 1.5)
        assert 'type="number"' in html
        assert 'step="0.5"' in html


# ---------------------------------------------------------------------------
# Dropdown / Select
# ---------------------------------------------------------------------------

class TestDropdown:
    def test_select_element(self):
        html = render_widget(_w("Dropdown", "grade", args={"options": ["A", "B", "C"]}), "B")
        assert "<select" in html
        assert "<option" in html

    def test_options_present(self):
        html = render_widget(_w("Dropdown", "grade", args={"options": ["A", "B", "C"]}), "A")
        assert ">A<" in html
        assert ">B<" in html
        assert ">C<" in html

    def test_selected_option(self):
        html = render_widget(_w("Dropdown", "grade", args={"options": ["A", "B", "C"]}), "B")
        assert 'value="B"  selected' in html

    def test_htmx_post(self):
        html = render_widget(_w("Dropdown", "grade", args={"options": []}), None)
        assert 'hx-post="/field/grade"' in html

    def test_select_alias(self):
        html = render_widget(_w("Select", "grade", args={"options": ["X"]}), "X")
        assert "<select" in html

    def test_options_labels_field_replaces_keys(self):
        html = render_widget(
            _w(
                "Dropdown",
                "focus_topic",
                args={
                    "options_field": "topic_keys",
                    "options_labels_field": "topic_labels",
                    "options": ["T0"],
                },
            ),
            "T0",
            data={
                "topic_keys": ["T0", "T1"],
                "topic_labels": {"T0": "Root theme", "T1": "Child theme"},
            },
        )
        assert 'value="T0"' in html
        assert ">Root theme<" in html
        assert ">Child theme<" in html
        assert ">T0<" not in html
        assert ">T1<" not in html


# ---------------------------------------------------------------------------
# SelectMultiple
# ---------------------------------------------------------------------------

class TestSelectMultiple:
    def test_multiple_attribute(self):
        html = render_widget(_w("SelectMultiple", "tags", args={"options": ["a", "b", "c"]}), ["a", "c"])
        assert "multiple" in html

    def test_selected_items(self):
        html = render_widget(_w("SelectMultiple", "tags", args={"options": ["a", "b", "c"]}), ["a", "c"])
        assert 'value="a"  selected' in html
        assert 'value="c"  selected' in html
        assert 'value="b"  selected' not in html


# ---------------------------------------------------------------------------
# RadioButtons
# ---------------------------------------------------------------------------

class TestRadioButtons:
    def test_fieldset_present(self):
        html = render_widget(_w("RadioButtons", "choice", args={"options": ["Yes", "No"]}), "Yes")
        assert "<fieldset" in html

    def test_radio_inputs(self):
        html = render_widget(_w("RadioButtons", "choice", args={"options": ["Yes", "No"]}), "Yes")
        assert 'type="radio"' in html

    def test_checked_option(self):
        html = render_widget(_w("RadioButtons", "choice", args={"options": ["Yes", "No"]}), "Yes")
        assert 'value="Yes"  checked' in html
        assert 'value="No"  checked' not in html


# ---------------------------------------------------------------------------
# Checkbox / Flag
# ---------------------------------------------------------------------------

class TestCheckbox:
    def test_checkbox_type(self):
        html = render_widget(_w("Checkbox", "done", args={"description": "Done?"}), True)
        assert 'type="checkbox"' in html

    def test_checked_when_true(self):
        html = render_widget(_w("Checkbox", "done"), True)
        assert "checked" in html

    def test_unchecked_when_false(self):
        html = render_widget(_w("Checkbox", "done"), False)
        assert "checked" not in html

    def test_flag_alias(self):
        html = render_widget(_w("Flag", "active"), True)
        assert 'type="checkbox"' in html

    def test_description_label(self):
        html = render_widget(_w("Checkbox", "done", args={"description": "Mark complete"}), False)
        assert "Mark complete" in html

    def test_string_false_unchecked(self):
        """Liquid soft-fill stores \"False\"; plain bool() would check it."""
        html = render_widget(_w("Checkbox", "done"), "False")
        assert "checked" not in html

    def test_string_true_checked(self):
        html = render_widget(_w("Checkbox", "done"), "True")
        assert "checked" in html

    def test_numeric_zero_unchecked(self):
        html = render_widget(_w("Checkbox", "done"), 0)
        assert "checked" not in html
        html = render_widget(_w("Checkbox", "done"), 0.0)
        assert "checked" not in html

    def test_numeric_one_checked(self):
        html = render_widget(_w("Checkbox", "done"), 1)
        assert "checked" in html

    def test_nan_unchecked(self):
        html = render_widget(_w("Checkbox", "done"), float("nan"))
        assert "checked" not in html

    def test_numpy_bool_false_unchecked(self):
        np = pytest.importorskip("numpy")
        html = render_widget(_w("Checkbox", "done"), np.bool_(False))
        assert "checked" not in html

    def test_complete_checkbox_string_false_unchecked(self):
        from referia.web.render import render_complete_checkbox

        html = render_complete_checkbox(
            "False", field="complete", record_index="alice"
        )
        assert "checked" not in html


# ---------------------------------------------------------------------------
# Combobox
# ---------------------------------------------------------------------------

class TestCombobox:
    def test_datalist_present(self):
        html = render_widget(_w("Combobox", "city", args={"options": ["London", "Paris"]}), "London")
        assert "<datalist" in html

    def test_input_has_list_attr(self):
        html = render_widget(_w("Combobox", "city", args={"options": []}), "")
        assert "list=" in html

    def test_options_in_datalist(self):
        html = render_widget(_w("Combobox", "city", args={"options": ["London", "Paris"]}), "")
        assert "London" in html
        assert "Paris" in html


# ---------------------------------------------------------------------------
# DatePicker
# ---------------------------------------------------------------------------

class TestDatePicker:
    def test_input_type_date(self):
        html = render_widget(_w("DatePicker", "dob"), "20001231")
        assert 'type="date"' in html

    def test_yyyymmdd_conversion(self):
        html = render_widget(_w("DatePicker", "dob"), "20001231")
        assert 'value="2000-12-31"' in html

    def test_iso_passthrough(self):
        html = render_widget(_w("DatePicker", "dob"), "2000-12-31")
        assert 'value="2000-12-31"' in html


# ---------------------------------------------------------------------------
# Label / HTML / HTMLMath / Markdown (viewer-style widgets)
# ---------------------------------------------------------------------------

class TestDisplayWidgets:
    def test_label(self):
        html = render_widget({"type": "Label", "field": "", "args": {"value": "Section A"}})
        assert "Section A" in html

    def test_html_passthrough(self):
        html = render_widget({"type": "HTML", "field": "", "args": {"value": "<b>bold</b>"}})
        assert "<b>bold</b>" in html

    def test_html_math_alias(self):
        html = render_widget({"type": "HTMLMath", "field": "", "args": {"value": "<em>x</em>"}})
        assert "<em>x</em>" in html

    def test_markdown_rendered(self):
        html = render_widget({"type": "Markdown", "field": "", "args": {"value": "**bold**"}})
        assert "<strong>" in html or "<b>" in html


# ---------------------------------------------------------------------------
# Button widgets
# ---------------------------------------------------------------------------

class TestButtons:
    def test_save_button(self):
        html = render_widget({"type": "SaveButton", "field": "", "args": {}})
        assert "<button" in html
        assert 'hx-post="/save"' in html
        assert 'hx-disabled-elt="this"' in html

    def test_save_button_has_no_hx_include(self):
        """Save button must NOT use hx-include to gather form data.
        Each field posts its own value via change/blur/mouseup events;
        Save just flushes the in-memory state to disk."""
        html = render_widget({"type": "SaveButton", "field": "", "args": {}})
        assert "hx-include" not in html

    def test_reload_button(self):
        html = render_widget({"type": "ReloadButton", "field": "", "args": {}})
        assert 'hx-post="/reload"' in html

    def test_populate_button(self):
        html = render_widget({"type": "PopulateButton", "field": "summary", "args": {}})
        assert 'hx-post="/populate/summary"' in html

    def test_populate_button_with_record_index_posts_index(self):
        html = render_widget(
            {
                "type": "PopulateButton",
                "field": "_segment",
                "args": {"description": "Segment document", "target": "units"},
            },
            record_index="doc-a",
        )
        assert 'hx-post="/populate/_segment"' in html
        assert "hx-vals=" in html
        assert "doc-a" in html
        assert 'hx-target="#review-panel"' in html
        assert 'hx-target="#status-bar"' not in html

    def test_populate_button_indicator_targets_target_field(self):
        """hx-indicator should point to the target field's widget container."""
        html = render_widget({"type": "PopulateButton", "field": "summary", "args": {}})
        assert 'hx-indicator="#widget-summary"' in html

    def test_populate_button_indicator_uses_args_target_when_present(self):
        """Complex format: button field is the route key; args.target is the indicator."""
        html = render_widget({
            "type": "PopulateButton",
            "field": "populate_btn",
            "args": {"target": "notes"},
        })
        # Unique button field → URL + container id; write target → spinner.
        assert 'hx-post="/populate/populate_btn"' in html
        assert 'hx-indicator="#widget-notes"' in html
        assert 'id="btn-widget-populate_btn"' in html
        assert 'id="btn-widget-notes"' not in html

    def test_populate_buttons_sharing_target_have_distinct_ids(self):
        """Multiple buttons with the same args.target must not share a DOM id."""
        from referia.web.render import render_widget as rw

        propose = rw({
            "type": "PopulateButton",
            "field": "_propose_split",
            "args": {"target": "uq_spec", "description": "Propose"},
        })
        confirm = rw(
            {
                "type": "PopulateButton",
                "field": "_confirm_split",
                "visible_if": "pending_proposal",
                "args": {"target": "uq_spec", "description": "Confirm"},
            },
            None,
            {"pending_proposal": None},
        )
        # Leading underscores are stripped by _widget_dom_id (CSS-safe rewrite).
        assert 'id="btn-widget-propose_split"' in propose
        assert 'id="btn-widget-confirm_split"' in confirm
        assert 'style="display:none"' in confirm
        shown = rw(
            {
                "type": "PopulateButton",
                "field": "_confirm_split",
                "visible_if": "pending_proposal",
                "args": {"target": "uq_spec", "description": "Confirm"},
            },
            None,
            {"pending_proposal": {"kind": "split"}},
        )
        assert 'style="display:none"' not in shown

    def test_populate_button_no_field_uses_args_target_for_url(self):
        """Introduction-style format: no top-level field, target from args.target."""
        html = render_widget({
            "type": "PopulateButton",
            "args": {
                "description": "Generate Summary",
                "target": "introSummary",
                "compute": {"field": "introSummary", "function": "llm_pdf_review"},
            },
        })
        assert 'hx-post="/populate/introSummary"' in html
        assert 'hx-indicator="#widget-introSummary"' in html

    def test_populate_button_args_compute_field_fallback(self):
        """When args.target absent but args.compute.field present, use compute field."""
        html = render_widget({
            "type": "PopulateButton",
            "args": {
                "compute": {"field": "chapterSummary", "function": "llm_pdf_review"},
            },
        })
        assert 'hx-post="/populate/chapterSummary"' in html
        assert 'hx-indicator="#widget-chapterSummary"' in html

    def test_populate_button_spaced_field_uses_safe_id_and_encoded_url(self):
        """Spaces in field names must not appear in ids or raw URL paths."""
        html = render_widget({
            "type": "PopulateButton",
            "field": "Importance Fairness",
            "args": {"description": "Check fair"},
        })
        assert 'hx-post="/populate/Importance%20Fairness"' in html
        assert 'hx-indicator="#widget-Importance_Fairness"' in html
        assert 'hx-indicator="#widget-Importance Fairness"' not in html
        assert 'id="btn-widget-Importance_Fairness"' in html

    def test_button_description(self):
        html = render_widget({"type": "SaveButton", "field": "", "args": {"description": "Save & Continue"}})
        assert "Save &amp; Continue" in html


# ---------------------------------------------------------------------------
# visible_if conditions
# ---------------------------------------------------------------------------

class TestVisibleIf:
    def test_hidden_when_dict_condition_false(self):
        spec = _w("Text", "detail", visible_if={"field": "show", "value": "yes"})
        html = render_widget(spec, "", data={"show": "no"})
        assert 'display:none' in html

    def test_visible_when_dict_condition_true(self):
        spec = _w("Text", "detail", visible_if={"field": "show", "value": "yes"})
        html = render_widget(spec, "", data={"show": "yes"})
        assert 'display:none' not in html

    def test_hidden_when_string_condition_falsy(self):
        spec = _w("Text", "detail", visible_if="active")
        html = render_widget(spec, "", data={"active": ""})
        assert 'display:none' in html

    def test_visible_when_string_condition_truthy(self):
        spec = _w("Text", "detail", visible_if="active")
        html = render_widget(spec, "", data={"active": "yes"})
        assert 'display:none' not in html

    def test_no_visible_if_always_shown(self):
        html = render_widget(_w("Text", "x"), "v", data={})
        assert 'display:none' not in html

    def test_string_false_hides_string_condition(self):
        """Checkbox soft-fill \"False\" must hide dependents (not bool(\"False\"))."""
        spec = _w("Textarea", "Email Comment", visible_if="Interview")
        html = render_widget(spec, "", data={"Interview": "False"})
        assert 'display:none' in html

    def test_bool_false_hides_string_condition(self):
        spec = _w("Textarea", "Email Comment", visible_if="Interview")
        html = render_widget(spec, "", data={"Interview": False})
        assert 'display:none' in html

    def test_numpy_bool_false_hides_string_condition(self):
        np = pytest.importorskip("numpy")
        spec = _w("Textarea", "Email Comment", visible_if="Interview")
        html = render_widget(spec, "", data={"Interview": np.bool_(False)})
        assert 'display:none' in html

    def test_dict_equals_alias(self):
        """visible_if dict may use equals (affected_widgets) as well as value."""
        spec = _w("Text", "detail", visible_if={"field": "Status", "equals": "yes"})
        assert 'display:none' in render_widget(spec, "", data={"Status": "no"})

    def test_dict_equals_yaml_bool_matches_yes_string(self):
        """Unquoted YAML yes/no become bools; Liquid fields emit 'yes'/'no'."""
        spec = _w("Text", "detail", visible_if={"field": "markedFlag", "equals": True})
        assert "display:none" not in render_widget(
            spec, "", data={"markedFlag": "yes"}
        )
        assert "display:none" in render_widget(
            spec, "", data={"markedFlag": "no"}
        )
        assert "display:none" in render_widget(
            spec, "", data={"markedFlag": "maybe"}
        )

    def test_dict_equals_yaml_bool_false_matches_no_and_empty(self):
        spec = _w("Text", "detail", visible_if={"field": "markedFlag", "equals": False})
        for value in ("no", "false", "0", "", None):
            assert "display:none" not in render_widget(
                spec, "", data={"markedFlag": value}
            )
        assert "display:none" in render_widget(
            spec, "", data={"markedFlag": "yes"}
        )

    def test_dict_equals_string_matches_checkbox_bool(self):
        """Quoted YAML 'yes' compared with a bool cell (swap branch)."""
        spec = _w("Text", "detail", visible_if={"field": "Flag", "equals": "yes"})
        assert "display:none" not in render_widget(
            spec, "", data={"Flag": True}
        )
        assert "display:none" in render_widget(
            spec, "", data={"Flag": False}
        )

    def test_dict_equals_identity_and_unrelated_strings(self):
        spec = _w("Text", "detail", visible_if={"field": "Flag", "equals": True})
        assert "display:none" not in render_widget(
            spec, "", data={"Flag": True}
        )
        spec_str = _w("Text", "detail", visible_if={"field": "Status", "equals": "foo"})
        assert "display:none" not in render_widget(
            spec_str, "", data={"Status": "foo"}
        )
        assert "display:none" in render_widget(
            spec_str, "", data={"Status": "bar"}
        )
        assert "display:none" in render_widget(
            spec, "", data={"Flag": None}
        )

    def test_dict_not_hides_when_field_truthy(self):
        """visible_if {field, not: true} hides when the field is set (Propose vs pending)."""
        spec = _w(
            "PopulateButton",
            "_propose_split",
            visible_if={"field": "pending_proposal", "not": True},
            args={"target": "uq_spec", "description": "Propose"},
        )
        hidden = render_widget(
            spec, None, {"pending_proposal": {"kind": "split"}}
        )
        shown = render_widget(spec, None, {"pending_proposal": None})
        assert 'display:none' in hidden
        assert 'display:none' not in shown
        assert 'display:none' not in render_widget(spec, "", data={"Status": "yes"})

    def test_dict_without_expected_uses_checkbox_truthiness(self):
        spec = _w("Text", "detail", visible_if={"field": "Interview"})
        assert 'display:none' in render_widget(spec, "", data={"Interview": "False"})
        assert 'display:none' not in render_widget(spec, "", data={"Interview": True})


# ---------------------------------------------------------------------------
# Unsupported type
# ---------------------------------------------------------------------------

class TestUnsupportedType:
    def test_comment_placeholder(self):
        html = render_widget({"type": "UnknownWidget", "field": "x", "args": {}})
        assert "<!--" in html
        assert "UnknownWidget" in html


# ---------------------------------------------------------------------------
# render_viewer
# ---------------------------------------------------------------------------

class TestRenderViewer:
    def test_markdown_viewer_renders_markup(self):
        html = render_viewer({"type": "Markdown"}, "**bold text**")
        assert "<strong>" in html or "<b>" in html
        assert 'class="viewer' in html

    def test_html_viewer_passthrough(self):
        html = render_viewer({"type": "HTML"}, "<p>raw</p>")
        assert "<p>raw</p>" in html

    def test_empty_content(self):
        html = render_viewer({"type": "Markdown"}, "")
        assert "viewer" in html

    def test_markdown_links_open_in_new_tab(self):
        html = render_viewer(
            {"type": "Markdown"},
            "[Course site](https://example.com/iei)",
        )
        assert 'href="https://example.com/iei"' in html
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html

    def test_html_viewer_links_open_in_new_tab(self):
        html = render_viewer(
            {"type": "HTML"},
            '<a href="https://example.com">site</a>',
        )
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html

    def test_existing_target_not_duplicated(self):
        html = render_viewer(
            {"type": "HTML"},
            '<a href="https://example.com" target="_self">stay</a>',
        )
        assert html.count("target=") == 1
        assert 'target="_self"' in html

    def test_existing_rel_kept_when_adding_target(self):
        """Links with rel but no target get target=_blank without a second rel."""
        html = render_viewer(
            {"type": "HTML"},
            '<a href="https://example.com" rel="nofollow">site</a>',
        )
        assert 'target="_blank"' in html
        assert html.count("rel=") == 1
        assert 'rel="nofollow"' in html

    def test_plotly_figure_emits_container_and_bindings(self):
        fig = {
            "data": [{"type": "scatter", "x": [1], "y": [2], "customdata": [{"phrase": "p"}]}],
            "layout": {},
        }
        spec = {
            "type": "PlotlyFigure",
            "field": "topic_scatter_spec",
            "on": {
                "click_point": [
                    {"set_field": "selected_phrase", "from": "customdata.phrase"},
                ]
            },
            "highlight": {"from_field": "selected_topic", "mode": "responsibility_ink"},
        }
        html = render_viewer(spec, figure=fig, viewer_index=3)
        assert 'class="viewer viewer-plotly"' in html
        assert 'id="viewer-plotly-3"' in html
        assert 'data-highlight-field="selected_topic"' in html
        assert "plotly-spec" in html
        assert "selected_phrase" in html
        assert "customdata.phrase" in html
        # JSON in <script> must be parseable (not html.escaped &quot;)
        assert "&quot;" not in html
        assert '"data"' in html or '\\"data\\"' in html

    def test_plotly_size_container_mode_attrs_and_layout(self):
        fig = {
            "data": [{"type": "scatter", "x": [1], "y": [2]}],
            "layout": {"height": 420, "width": 600},
        }
        html = render_viewer(
            {
                "type": "PlotlyFigure",
                "size": {"mode": "container", "observe": True},
            },
            figure=fig,
            viewer_index=0,
        )
        assert 'data-size-mode="container"' in html
        assert 'data-size-observe="1"' in html
        assert "viewer-plotly--fill" in html
        assert 'data-size-aspect="4/3"' in html
        assert "--plotly-aspect: 4/3" in html
        assert '"autosize": true' in html or '"autosize":true' in html
        assert '"height"' not in html.split("plotly-spec")[1].split("</script>")[0]

    def test_plotly_size_observe_false(self):
        html = render_viewer(
            {"type": "PlotlyFigure", "size": {"mode": "figure", "observe": False}},
            figure={"data": [], "layout": {}},
            viewer_index=0,
        )
        assert 'data-size-observe="0"' in html
        assert "viewer-plotly--fill" not in html

    def test_static_image_viewer(self):
        html = render_viewer(
            {"type": "StaticImage"},
            "https://example.com/a.png",
            viewer_index=1,
        )
        assert 'class="viewer viewer-image"' in html
        assert 'src="https://example.com/a.png"' in html

    def test_plotly_figure_without_data_emits_empty_placeholder(self):
        html = render_viewer(
            {"type": "PlotlyFigure"},
            figure=None,
            viewer_index=0,
        )
        assert "viewer-plotly-0" in html
        assert "No figure data" in html or "plotly-spec" in html

    def test_collapse_wraps_matching_headings_only(self):
        md = (
            "## Exchange 1\n\n"
            "### User\n\n"
            "why entropy?\n\n"
            "### LLM\n\n"
            "Because von Neumann said so.\n\n"
            "### User\n\n"
            "and then?\n"
        )
        html = render_viewer(
            {"type": "Markdown", "collapse": {"headings": ["LLM"]}},
            md,
        )
        assert html.count('<details class="viewer-heading-collapse"') == 1
        assert "<summary>LLM</summary>" in html
        assert "von Neumann" in html
        assert "why entropy?" in html
        # User prompts stay in the open flow, not inside the details body.
        details_start = html.index('<details class="viewer-heading-collapse"')
        details_end = html.index("</details>", details_start)
        wrapped = html[details_start:details_end]
        assert "von Neumann" in wrapped
        assert "why entropy?" not in wrapped
        assert "and then?" not in wrapped
        assert "Exchange 1" in html
        assert 'open' not in wrapped.split(">")[0]

    def test_collapse_absent_leaves_headings(self):
        html = render_viewer({"type": "Markdown"}, "### LLM\n\nsecret")
        assert "viewer-heading-collapse" not in html
        assert "secret" in html

    def test_collapse_default_open(self):
        html = render_viewer(
            {
                "type": "Markdown",
                "collapse": {"headings": ["LLM"], "default": "open"},
            },
            "### LLM\n\nbody",
        )
        assert 'class="viewer-heading-collapse"' in html
        assert " open" in html.split("viewer-heading-collapse")[1].split(">")[0]

    def test_collapse_first_word_and_case(self):
        html = render_viewer(
            {"type": "Markdown", "collapse": {"headings": ["llm"]}},
            "### LLM reply\n\nhidden\n",
        )
        assert "<summary>LLM reply</summary>" in html
        assert "hidden" in html
        assert 'data-section-key="llm-reply-1"' in html

    def test_collapse_html_viewer(self):
        html = render_viewer(
            {"type": "HTML", "collapse": {"headings": ["LLM"]}},
            "<h3>LLM</h3><p>reply</p><h3>User</h3><p>ask</p>",
        )
        assert html.count("viewer-heading-collapse") == 1
        assert "reply" in html
        wrapped = html[
            html.index("viewer-heading-collapse") : html.index("</details>")
        ]
        assert "reply" in wrapped
        assert "ask" not in wrapped

    def test_plotly_applies_highlight_opacity(self):
        fig = {
            "data": [
                {
                    "type": "scatter",
                    "x": [0, 1],
                    "y": [0, 1],
                    "customdata": [{"topic": "A"}, {"topic": "B"}],
                }
            ],
            "layout": {},
        }
        html = render_viewer(
            {
                "type": "PlotlyFigure",
                "highlight": {"from_field": "selected_topic", "mode": "default"},
            },
            figure=fig,
            highlight_value="B",
            viewer_index=0,
        )
        assert "0.25" in html
        assert "1.0" in html or "1" in html

    def test_visible_if_hides_markdown_viewer(self):
        html = render_viewer(
            {"type": "Markdown", "visible_if": "ch8Present"},
            "Chapter 8",
            data={"ch8Present": False},
        )
        assert "display:none" in html
        assert "Chapter 8" in html

    def test_visible_if_shows_markdown_viewer(self):
        html = render_viewer(
            {"type": "Markdown", "visible_if": "ch8Present"},
            "Chapter 8",
            data={"ch8Present": True},
        )
        assert "display:none" not in html
        assert "Chapter 8" in html

    def test_visible_if_equals_and_not(self):
        hidden = render_viewer(
            {
                "type": "Markdown",
                "visible_if": {"field": "Status", "equals": "yes"},
            },
            "gated",
            data={"Status": "no"},
        )
        shown = render_viewer(
            {
                "type": "Markdown",
                "visible_if": {"field": "pending_proposal", "not": True},
            },
            "ready",
            data={"pending_proposal": False},
        )
        assert "display:none" in hidden
        assert "display:none" not in shown

    def test_without_visible_if_unchanged(self):
        html = render_viewer({"type": "Markdown"}, "**bold**")
        assert "display:none" not in html
        assert "viewer-markdown" in html

    def test_visible_if_hides_html_and_image_viewers(self):
        html = render_viewer(
            {"type": "HTML", "visible_if": "ch8Present"},
            "<p>Chapter 8</p>",
            viewer_index=2,
            data={"ch8Present": False},
        )
        assert "display:none" in html
        assert 'id="viewer-html-2"' in html
        assert "<p>Chapter 8</p>" in html

        image = render_viewer(
            {"type": "StaticImage", "visible_if": "ch8Present"},
            "https://example.com/ch8.png",
            viewer_index=3,
            data={"ch8Present": "False"},
        )
        assert "display:none" in image
        assert 'id="viewer-image-3"' in image
        assert "https://example.com/ch8.png" in image

    def test_visible_if_shows_htmlmath_viewer(self):
        html = render_viewer(
            {"type": "HTMLMath", "visible_if": "ch8Present"},
            "$x^2$",
            viewer_index=1,
            data={"ch8Present": True},
        )
        assert "display:none" not in html
        assert 'id="viewer-markdown-1"' in html

    def test_visible_if_merges_plotly_aspect_style(self):
        html = render_viewer(
            {
                "type": "PlotlyFigure",
                "visible_if": "ch8Present",
                "size": {"mode": "container", "aspect_ratio": "16/9"},
            },
            figure={"data": [], "layout": {}},
            viewer_index=4,
            data={"ch8Present": False},
        )
        assert html.count(" style=") == 1
        assert "display:none" in html
        assert "--plotly-aspect: 16/9" in html
        assert 'id="viewer-plotly-4"' in html
        assert "plotly-spec" in html

    def test_visible_if_without_row_data_hides(self):
        html = render_viewer(
            {"type": "Markdown", "visible_if": "ch8Present"},
            "Chapter 8",
        )
        assert "display:none" in html
        assert "Chapter 8" in html


class TestCombineHtmlStyles:
    def test_merges_style_fragments(self):
        combined = _combine_html_styles(
            ' style="--plotly-aspect: 16/9"',
            ' style="display:none"',
        )
        assert combined == ' style="--plotly-aspect: 16/9; display:none"'

    def test_skips_empty_and_bare_values(self):
        assert _combine_html_styles("", None) == ""
        assert _combine_html_styles("display:none") == ' style="display:none"'


# ---------------------------------------------------------------------------
# render_form
# ---------------------------------------------------------------------------

class TestRenderForm:
    def test_form_element_present(self):
        html = render_form([], {})
        assert "<form" in html
        assert "</form>" in html

    def test_form_id(self):
        html = render_form([], {})
        assert 'id="review-form"' in html

    def test_fields_rendered(self):
        specs = [
            _w("Text", "first_name"),
            _w("Textarea", "bio"),
        ]
        html = render_form(specs, {"first_name": "Alice", "bio": "A reviewer."})
        assert 'name="first_name"' in html
        assert 'name="bio"' in html
        assert "Alice" in html
        assert "A reviewer." in html

    def test_values_looked_up_from_data(self):
        specs = [_w("Text", "city")]
        html = render_form(specs, {"city": "Cambridge"})
        assert "Cambridge" in html

    def test_missing_field_value_is_empty(self):
        specs = [_w("Text", "missing")]
        html = render_form(specs, {})
        assert 'value=""' in html

    def test_section_entries_open_collapsible_group(self):
        """type: Section with indented entries: wraps children in <details>."""
        specs = [
            {
                "type": "Section",
                "title": "Chapter 1",
                "entries": [
                    _w("Textarea", "ch1Summary", args={"description": "Summary"}),
                ],
            },
            {
                "type": "Section",
                "title": "Chapter 2",
                "entries": [
                    _w("Textarea", "ch2Summary", args={"description": "Summary"}),
                ],
            },
        ]
        html = render_form(specs, {"ch1Summary": "a", "ch2Summary": "b"})
        assert html.count('<details class="review-section"') == 2
        assert 'data-section-key="0/chapter-1"' in html
        assert 'data-section-key="1/chapter-2"' in html
        assert "<summary>Chapter 1</summary>" in html
        assert "<summary>Chapter 2</summary>" in html
        assert 'name="ch1Summary"' in html
        assert 'name="ch2Summary"' in html
        # Title is summary only — not a Markdown heading in the body
        assert "widget-markdown" not in html

    def test_inherited_section_omits_absent_present_flags(self):
        specs = [
            {
                "type": "Section",
                "title": "PDF pages",
                "inherited": True,
                "writable": False,
                "entries": [
                    _w("Checkbox", "ch1Present", args={"description": "Chapter 1 present"}),
                    _w("Checkbox", "ch8Present", args={"description": "Chapter 8 present"}),
                ],
            }
        ]
        html = render_form(specs, {"ch1Present": True, "ch8Present": False})
        assert "Chapter 1 present" in html
        assert "Chapter 8 present" not in html

    def test_heading_markdown_does_not_open_section(self):
        """Bare ### Markdown is not a section (must use nested entries)."""
        specs = [
            {"type": "Markdown", "liquid": "### Chapter 1"},
            _w("Textarea", "ch1Summary"),
        ]
        html = render_form(specs, {"ch1Summary": "a"})
        assert "review-section" not in html
        assert "widget-markdown" in html
        assert 'name="ch1Summary"' in html

    def test_preamble_then_nested_section(self):
        specs = [
            _w("Text", "overall", args={"description": "Overall"}),
            {
                "type": "Section",
                "title": "Notes",
                "entries": [_w("Textarea", "notes")],
            },
        ]
        html = render_form(specs, {"overall": "x", "notes": "y"})
        assert 'name="overall"' in html
        assert html.index('name="overall"') < html.index('<details class="review-section"')
        assert "<summary>Notes</summary>" in html
        assert 'name="notes"' in html

    def test_section_without_entries_is_empty_details(self):
        """A Section with no children still renders a closed details shell."""
        specs = [{"type": "Section", "title": "Empty"}]
        html = render_form(specs, {})
        assert '<details class="review-section"' in html
        assert "<summary>Empty</summary>" in html
        # Sibling after the section is not swallowed
        specs2 = [
            {"type": "Section", "title": "Empty", "entries": []},
            _w("Text", "after"),
        ]
        html2 = render_form(specs2, {"after": "x"})
        assert 'name="after"' in html2
        assert html2.index("</details>") < html2.index('name="after"')

    def test_section_collapse_false_is_static(self):
        """args.collapse: false keeps cache-style chrome out of <details>."""
        specs = [
            {
                "type": "Section",
                "title": "Extract parameters",
                "entries": [_w("Text", "phrase_kinds")],
            },
            {
                "type": "Section",
                "title": "Cache",
                "args": {"collapse": False},
                "entries": [
                    {
                        "type": "HTML",
                        "args": {
                            "value": '<p class="chrome-hint">Reload from disk.</p>'
                        },
                    },
                    _w("ReloadButton", "_reload", args={"description": "Reload cache"}),
                ],
            },
        ]
        html = render_form(specs, {"phrase_kinds": "benefit"})
        assert '<details class="review-section"' in html
        assert "<summary>Extract parameters</summary>" in html
        assert 'class="review-section review-section-static"' in html
        assert "<h3>Cache</h3>" in html
        assert "chrome-hint" in html
        assert "Reload cache" in html
        assert "<summary>Cache</summary>" not in html


# ---------------------------------------------------------------------------
# Criterion widget
# ---------------------------------------------------------------------------

class TestCriterionWidget:
    """Criterion widgets display read-only criterion text from a liquid: key."""

    def test_renders_liquid_column_reference(self):
        """{{colName}} in liquid: is replaced with data value."""
        spec = {"type": "Criterion", "liquid": "{{summaryText}}"}
        html = render_widget(spec, None, data={"summaryText": "Be concise and clear."})
        assert "Be concise and clear." in html
        assert "widget-criterion" in html

    def test_renders_multiline_liquid(self):
        spec = {"type": "Criterion", "liquid": "**Strong**: {{criterion}}\n"}
        html = render_widget(spec, None, data={"criterion": "Meets expectations"})
        assert "Meets expectations" in html

    def test_missing_column_renders_empty(self):
        spec = {"type": "Criterion", "liquid": "{{missingCol}}"}
        html = render_widget(spec, None, data={})
        assert "widget-criterion" in html
        # Missing key renders as empty string — no raw {{missingCol}} in output
        assert "{{missingCol}}" not in html

    def test_no_liquid_renders_empty_criterion(self):
        spec = {"type": "Criterion"}
        html = render_widget(spec, None, data={})
        assert "widget-criterion" in html

    def test_static_markdown_in_liquid(self):
        """Static text (after %param% substitution) renders as markdown."""
        spec = {"type": "Criterion", "liquid": "### Introduction"}
        html = render_widget(spec, None, data={})
        # Should render as an <h3>
        assert "<h3>" in html

    def test_if_tag_in_criterion_liquid(self):
        spec = {
            "type": "Criterion",
            "liquid": (
                "**Scheduled:** {% if interviewTime %}{{interviewTime}}"
                "{% elsif scheduledStartTime %}{{scheduledStartTime}}{% endif %}"
            ),
        }
        html = render_widget(spec, None, data={"interviewTime": "15:00"})
        assert "15:00" in html
        assert "{% if" not in html
        assert "scheduledStartTime" not in html

    def test_elsif_used_when_interview_time_missing(self):
        spec = {
            "type": "Criterion",
            "liquid": (
                "{% if interviewTime %}{{interviewTime}}"
                "{% elsif scheduledStartTime %}{{scheduledStartTime}}{% endif %}"
            ),
        }
        html = render_widget(spec, None, data={"scheduledStartTime": "09:30"})
        assert "09:30" in html
        assert "{% if" not in html
        assert "interviewTime" not in html


# ---------------------------------------------------------------------------
# Markdown widget top-level liquid: key
# ---------------------------------------------------------------------------

class TestMarkdownTopLevelLiquid:
    """Markdown widgets pick up content from the top-level liquid: key."""

    def test_renders_static_liquid_content(self):
        spec = {"type": "Markdown", "liquid": "### Chapter 1"}
        html = render_widget(spec, None, data={})
        assert "<h3>" in html
        assert "Chapter 1" in html

    def test_liquid_takes_priority_over_args_description(self):
        spec = {
            "type": "Markdown",
            "liquid": "### From Liquid",
            "args": {"description": "From args"},
        }
        html = render_widget(spec, None, data={})
        assert "From Liquid" in html
        assert "From args" not in html

    def test_args_liquid_with_column_reference(self):
        """CriterionComment expansion puts liquid: inside args; column refs must resolve."""
        spec = {
            "name": "Summary Criterion",
            "type": "Markdown",
            "args": {"layout": {"width": "800px"}, "liquid": "{{introductionSummaryCriterion}}\n"},
        }
        data = {"introductionSummaryCriterion": "**Thesis summary** should be concise."}
        html = render_widget(spec, None, data=data)
        assert "Thesis summary" in html
        assert "{{introductionSummaryCriterion}}" not in html

    def test_args_liquid_missing_column_is_empty(self):
        """Missing column in args.liquid resolves to empty string — no raw {{key}} shown."""
        spec = {
            "type": "Markdown",
            "args": {"liquid": "{{missingColumn}}\n"},
        }
        html = render_widget(spec, None, data={})
        assert "{{missingColumn}}" not in html

    def test_top_level_liquid_with_column_reference(self):
        """Interview Markdown widgets put {{column}} on the top-level liquid key."""
        spec = {
            "type": "Markdown",
            "liquid": "### Question 1\n\n{{q1Question}}\n\n1. {{q1pt1Question}}\n",
        }
        data = {
            "q1Question": "Consider a program that runs over the integers.",
            "q1pt1Question": "How many integers might we expect to include?",
        }
        html = render_widget(spec, None, data=data)
        assert "Consider a program that runs over the integers." in html
        assert "How many integers might we expect to include?" in html
        assert "{{q1Question}}" not in html
        assert "{{q1pt1Question}}" not in html

    def test_top_level_liquid_missing_column_is_empty(self):
        """Missing column in top-level liquid resolves to empty — no raw {{key}}."""
        spec = {"type": "Markdown", "liquid": "Question 1\n{{q1Question}}\n"}
        html = render_widget(spec, None, data={})
        assert "{{q1Question}}" not in html

    def test_if_tag_shows_section_when_value_present(self):
        spec = {
            "type": "Markdown",
            "liquid": (
                "### Application\n"
                "{% if candidateEmail %}Email: {{candidateEmail}}{% endif %}\n"
            ),
        }
        html = render_widget(
            spec, None, data={"candidateEmail": "salonee.verma.05@gmail.com"}
        )
        assert "salonee.verma.05@gmail.com" in html
        assert "{% if" not in html
        assert "{% endif %}" not in html

    def test_if_tag_hides_section_when_value_missing(self):
        spec = {
            "type": "Markdown",
            "liquid": (
                "{% if preliminaryResearchComment %}"
                "Preliminary Research Comment\n"
                "{{preliminaryResearchComment}}"
                "{% endif %}"
            ),
        }
        html = render_widget(spec, None, data={})
        assert "Preliminary Research Comment" not in html
        assert "{% if" not in html

    def test_mapped_alias_substitutes_in_if(self):
        spec = {
            "type": "Markdown",
            "liquid": "{% if Title %}**{{Title}}**{% endif %}",
        }
        html = render_widget(spec, None, data={"Title": "Toolkit for misuse"})
        assert "Toolkit for misuse" in html
        assert "{% if" not in html

    def test_invalid_liquid_does_not_dump_template(self):
        spec = {"type": "Markdown", "liquid": "{% if %}broken{% endif %}"}
        html = render_widget(spec, None, data={})
        assert "{% if %}" not in html
        assert "broken" not in html

    def test_elsif_else_chain_matches_interview_start_widget(self):
        spec = {
            "type": "Markdown",
            "liquid": (
                "{% if interviewTime %}{{interviewTime}}"
                "{% elsif scheduledStartTime %}{{scheduledStartTime}}"
                "{% elsif scheduledStart %}{{scheduledStart}}"
                "{% else %}unscheduled{% endif %}"
            ),
        }
        html = render_widget(spec, None, data={"scheduledStart": "16:00"})
        assert "16:00" in html
        assert "unscheduled" not in html
        html = render_widget(spec, None, data={})
        assert "unscheduled" in html
        assert "{% else %}" not in html

    def test_unless_and_for_tags(self):
        spec = {
            "type": "Markdown",
            "liquid": (
                "{% unless withdrawn %}Active{% endunless %}\n"
                "{% for item in items %}- {{item}}\n{% endfor %}"
            ),
        }
        html = render_widget(
            spec, None, data={"withdrawn": "", "items": ["one", "two"]}
        )
        assert "Active" in html
        assert "one" in html
        assert "two" in html
        html = render_widget(spec, None, data={"withdrawn": "yes", "items": []})
        assert "Active" not in html
        assert "{% for" not in html

    def test_nan_and_empty_values_are_stripped_before_if(self):
        spec = {
            "type": "Markdown",
            "liquid": "{% if candidateEmail %}Email: {{candidateEmail}}{% endif %}",
        }
        html = render_widget(spec, None, data={"candidateEmail": float("nan")})
        assert "Email:" not in html
        html = render_widget(spec, None, data={"candidateEmail": ""})
        assert "Email:" not in html
        assert math.isnan(float("nan"))

    def test_empty_top_level_liquid_falls_through_to_args(self):
        spec = {
            "type": "Markdown",
            "liquid": "",
            "args": {"liquid": "From args.liquid"},
        }
        html = render_widget(spec, None, data={})
        assert "From args.liquid" in html

    def test_markdown_content_skips_evaluation_without_row_data(self):
        spec = {
            "type": "Markdown",
            "liquid": "{% if interviewTime %}{{interviewTime}}{% endif %}",
        }
        assert "{% if" in _markdown_widget_content(spec, None, data=None)


class TestEvaluateLiquid:
    """Direct coverage of python-liquid evaluation and registered filters."""

    def test_empty_or_missing_template_is_empty_string(self):
        assert _evaluate_liquid("", {"a": 1}) == ""
        assert _evaluate_liquid(None, {"a": 1}) == ""

    def test_none_data_renders_against_empty_context(self):
        assert _evaluate_liquid("static", None) == "static"
        assert "{{x}}" not in _evaluate_liquid("{{x}}", None)

    def test_environment_is_cached(self):
        assert _liquid_environment() is _liquid_environment()

    def test_registered_filters(self):
        assert "%20" in _evaluate_liquid("{{ path | url_escape }}", {"path": "a b"})
        html = _evaluate_liquid("{{ text | markdownify }}", {"text": "**bold**"})
        assert "bold" in html
        assert "<" in html
        assert _evaluate_liquid("{{ n | to_i }}", {"n": "3.9"}) == "3"
        assert "/notebooks/foo" in _evaluate_liquid(
            "{{ path | relative_url }}", {"path": "foo"}
        )
        abs_url = _evaluate_liquid("{{ path | absolute_url }}", {"path": "foo"})
        assert abs_url.startswith("http://")
        assert abs_url.endswith("foo")

    def test_evaluation_exception_logs_and_returns_empty(self, caplog, monkeypatch):
        def boom(_template):
            raise RuntimeError("boom")

        monkeypatch.setattr(_liquid_environment(), "from_string", boom)
        with caplog.at_level(logging.ERROR, logger="referia.web.render"):
            assert _evaluate_liquid("{{x}}", {"x": 1}) == ""
        assert "Liquid evaluation failed" in caplog.text
        assert "boom" in caplog.text

    def test_unknown_filter_does_not_dump_source(self):
        rendered = _evaluate_liquid("{{ x | no_such_filter }}", {"x": "keep"})
        assert rendered == ""
        assert "no_such_filter" not in rendered
        assert "keep" not in rendered


class TestRenderDocumentPanel:
    def test_empty_when_no_docs(self):
        from referia.web.render import render_document_panel

        assert render_document_panel([], []) == ""

    def test_urls_are_links(self):
        from referia.web.render import render_document_panel

        html = render_document_panel([], [{"href": "https://example.com/a", "label": "A"}])
        assert 'href="https://example.com/a"' in html
        assert 'target="_blank"' in html

    def test_pdf_iframe_uses_prefix(self):
        from referia.web.render import render_document_panel

        html = render_document_panel(
            [{"kind": "localpdf", "n": 0, "label": "thesis", "exists": True}],
            [],
            prefix="/theses/examined",
            current_index="alice",
        )
        assert 'src="/theses/examined/record-document/localpdf/0?index=alice"' in html
        assert "thesis" in html

    def test_pdf_iframe_includes_index_query(self):
        from referia.web.render import render_document_panel

        html = render_document_panel(
            [{"kind": "editpdf", "n": 0, "label": "proposal", "exists": True}],
            [],
            current_index=2,
        )
        assert 'src="/record-document/editpdf/0?index=2"' in html
        assert 'href="/record-document/editpdf/0?index=2"' in html

    def test_pdf_entry_has_stable_doc_key(self):
        from referia.web.render import render_document_panel

        html = render_document_panel(
            [{"kind": "editpdf", "n": 0, "label": "proposal", "exists": True}],
            [],
            current_index="alice",
        )
        assert 'data-doc-key="editpdf/0"' in html
        assert 'class="pdf-entry"' in html

    def test_missing_pdf_has_no_iframe(self):
        from referia.web.render import render_document_panel

        html = render_document_panel(
            [{"kind": "editpdf", "n": 1, "label": "ch1", "exists": False}],
            [],
            current_index="bob",
        )
        assert "<iframe" not in html
        assert "PDF not found" in html

    def test_editpdf_prepare_button(self):
        from referia.web.render import render_document_panel

        html = render_document_panel(
            [{"kind": "editpdf", "n": 0, "label": "proposal", "exists": True}],
            [],
            current_index="alice",
        )
        assert 'hx-post="/edit-pdf/0"' in html
        assert "Prepare / download PDF" in html

    def test_panel_omits_create_document_buttons(self):
        from referia.web.render import render_document_panel

        html = render_document_panel(
            [{"kind": "editpdf", "n": 0, "label": "proposal", "exists": True}],
            [],
            current_index="alice",
        )
        assert "generate-document" not in html
        assert "nav-document-actions" not in html

    def test_visible_if_hides_missing_chapter_pdf(self):
        from referia.web.render import render_document_panel

        html = render_document_panel(
            [
                {
                    "kind": "editpdf",
                    "n": 0,
                    "label": "thesis_ch1",
                    "exists": True,
                    "visible_if": "ch1Present",
                },
                {
                    "kind": "editpdf",
                    "n": 1,
                    "label": "thesis_ch8",
                    "exists": False,
                    "visible_if": "ch8Present",
                },
            ],
            [],
            data={"ch1Present": True, "ch8Present": False},
        )
        assert "thesis_ch1" in html
        assert "thesis_ch8" not in html
        assert "PDF not found" not in html


class TestRenderDocumentActions:
    def test_empty_when_no_actions(self):
        from referia.web.render import render_document_actions

        assert render_document_actions() == ""
        assert render_document_actions([], []) == ""

    def test_document_buttons_rendered(self):
        from referia.web.render import render_document_actions

        html = render_document_actions(
            documents=[{"n": 0, "type": "docx", "label": "Create docx", "summary": False}],
            summary_documents=[
                {"n": 0, "type": "letter", "label": "Create Summary letter", "summary": True}
            ],
        )
        assert 'class="nav-document-actions"' in html
        assert 'id="nav-document-actions"' in html
        assert 'hx-post="/generate-document/0"' in html
        assert 'hx-post="/generate-summary-document/0"' in html
        assert "Create docx" in html
        assert "Create Summary letter" in html

    def test_visible_if_hides_gated_button(self):
        from referia.web.render import render_document_actions

        entries = [
            {
                "n": 0,
                "type": "email",
                "label": "Create Email",
                "summary": False,
                "visible_if": "Interview",
            }
        ]
        hidden = render_document_actions(documents=entries, data={"Interview": False})
        assert "Create Email" not in hidden
        assert 'id="nav-document-actions"' in hidden

        shown = render_document_actions(documents=entries, data={"Interview": True})
        assert "Create Email" in shown
        assert 'hx-post="/generate-document/0"' in shown

    def test_record_index_adds_hx_vals_and_unique_id(self):
        from referia.web.render import render_document_actions

        html = render_document_actions(
            documents=[{"n": 0, "type": "email", "label": "Email feedback"}],
            record_index="ua257",
            container_id="row-document-actions-ua257",
        )
        assert 'id="row-document-actions-ua257"' in html
        assert "row-document-actions" in html
        assert "hx-vals=" in html
        assert "ua257" in html
        assert 'hx-post="/generate-document/0"' in html

    def test_visible_if_string_false_hides_button(self):
        from referia.web.render import render_document_actions

        entries = [
            {
                "n": 0,
                "type": "email",
                "label": "Create Email",
                "summary": False,
                "visible_if": "Interview",
            }
        ]
        html = render_document_actions(documents=entries, data={"Interview": "False"})
        assert "Create Email" not in html

    def test_without_data_ignores_visible_if(self):
        """When data is omitted (legacy callers), buttons still render."""
        from referia.web.render import render_document_actions

        html = render_document_actions(
            documents=[
                {
                    "n": 0,
                    "type": "email",
                    "label": "Create Email",
                    "summary": False,
                    "visible_if": "Interview",
                }
            ]
        )
        assert "Create Email" in html


class TestInlineListRecordIndex:
    def test_hx_vals_and_scoped_dom_id(self):
        from referia.web.render import render_widget, render_form, render_filter_bar

        html = render_widget(_w("Checkbox", "complete"), True, record_index="cfg/a")
        assert 'hx-vals="' in html
        assert "cfg/a" in html or "cfg" in html
        assert 'id="widget-complete-' in html

        form = render_form([_w("Text", "notes")], {"notes": ""}, record_index="r1")
        assert 'id="review-form-r1"' in form
        assert "hx-vals=" in form

        bar = render_filter_bar(
            [
                {"field": "complete", "type": "boolean", "label": "Done"},
                {"field": "title", "type": "contains", "label": "Title"},
            ],
            [{"field": "date", "order": "desc"}],
            {
                "complete": "any",
                "title": {"query": "admissions", "mode": "words"},
            },
        )
        assert 'hx-post="/filters"' in bar
        assert "filter__complete" in bar
        assert 'class="filters inline-listing-filters"' in bar
        assert 'name="group"' in bar
        assert "Group by" in bar
        assert 'value="directory"' in bar
        assert 'value="version"' in bar
        assert 'value="month"' in bar
        assert 'value="none"' in bar
        assert 'name="filter__title__query"' in bar
        assert 'value="admissions"' in bar
        assert 'name="filter__title__mode"' in bar
        assert 'value="words" selected' in bar

        bar_ver = render_filter_bar([], [], {"_group": "version"})
        assert 'value="version" selected' in bar_ver
        bar_month = render_filter_bar([], [], {"_group": "month"})
        assert 'value="month" selected' in bar_month
        bar_none = render_filter_bar([], [], {"_group": "none"})
        assert 'value="none" selected' in bar_none

    def test_boolean_filter_invalid_value_falls_back_to_any(self):
        """Unknown boolean filter state must select Any, not a blank option."""
        from referia.web.render import render_filter_bar

        bar = render_filter_bar(
            [{"field": "complete", "type": "boolean", "label": "Done"}],
            [],
            {"complete": "Maybe"},
        )
        # Invalid values coerce to any (see render_filter_bar boolean branch).
        assert 'value="any" selected' in bar
        assert 'value="true" selected' not in bar
        assert 'value="false" selected' not in bar

    def test_boolean_filter_title_case_any_selected(self):
        from referia.web.render import render_filter_bar

        bar = render_filter_bar(
            [{"field": "complete", "type": "boolean", "label": "Done"}],
            [],
            {"complete": "Any"},
        )
        assert 'value="any" selected' in bar


class TestInlineListing:
    def test_directory_listing_shape_with_complete_checkbox(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "spring",
                    "href": "/spring/",
                    "group": "",
                    "data": {
                        "title": "Spring reviews",
                        "date": "2026-03-01",
                        "description": "Q1 work",
                        "complete": False,
                        "referia_config_version": 1,
                    },
                },
                {
                    "index": "autumn",
                    "href": "/autumn/",
                    "group": "",
                    "data": {
                        "title": "Autumn reviews",
                        "date": "2026-09-15",
                        "description": "Q3 work",
                        "complete": True,
                        "referia_config_version": 2,
                    },
                },
            ],
            [
                {"type": "Checkbox", "field": "complete", "args": {"description": "Complete"}},
                {"type": "SaveButton"},
            ],
        )
        assert 'class="inline-listing"' in html
        assert 'class="complete-check"' in html
        assert "complete-check-label" in html
        assert "Done" in html
        assert "Select all filtered" in html
        assert 'hx-post="/field-bulk/complete"' in html
        assert "select-all-entry" in html
        assert "Spring reviews" in html
        assert "Autumn reviews" in html
        assert 'href="/spring/"' in html
        assert 'target="_blank"' in html
        assert "badge-complete" in html
        assert "badge-version" in html
        assert "v1" in html
        assert "v2" in html
        assert "Q1 work" in html
        assert "entry-extras" not in html
        assert "SaveButton" not in html
        # select-all + two row checkboxes
        assert html.count('type="checkbox"') == 3

    def test_empty_listing_message(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing([], [{"type": "Checkbox", "field": "complete"}])
        assert "No rows match" in html
        assert "Select all filtered" not in html

    def test_group_heading_style_by_mode(self):
        from referia.web.render import render_inline_listing

        entries = [
            {
                "index": "a",
                "group": "templates",
                "data": {"title": "A", "complete": False},
            }
        ]
        specs = [{"type": "Checkbox", "field": "complete"}]
        by_dir = render_inline_listing(entries, specs, group_by="directory")
        assert "<h2>templates/</h2>" in by_dir
        by_ver = render_inline_listing(
            [{"index": "a", "group": "v2", "data": {"title": "A", "complete": False}}],
            specs,
            group_by="version",
        )
        assert "<h2>v2</h2>" in by_ver
        assert "<h2>v2/</h2>" not in by_ver
        by_month = render_inline_listing(
            [{"index": "a", "group": "2026-10", "data": {"title": "A", "complete": False}}],
            specs,
            group_by="month",
        )
        assert "<h2>2026-10</h2>" in by_month
        assert "<h2>2026-10/</h2>" not in by_month
        by_none = render_inline_listing(
            [{"index": "a", "group": "", "data": {"title": "A", "complete": False}}],
            specs,
            group_by="none",
        )
        assert "<h2>" not in by_none

    def test_detail_field_renders_collapsible_when_present(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "talk-a",
                    "data": {
                        "title": "Talk A",
                        "description": "subtitle · venue",
                        "abstract": "Long abstract about the talk.",
                        "complete": False,
                    },
                },
                {
                    "index": "talk-b",
                    "data": {
                        "title": "Talk B",
                        "abstract": "",
                        "complete": False,
                    },
                },
            ],
            [{"type": "Checkbox", "field": "complete"}],
            detail_field="abstract",
        )
        assert 'class="entry-detail"' in html
        assert 'data-detail-field="abstract"' in html
        assert "<summary>Abstract</summary>" in html
        assert "Long abstract about the talk." in html
        # Empty abstract: only one details block (talk-a)
        assert html.count('class="entry-detail"') == 1

    def test_detail_field_omitted_by_default(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "talk-a",
                    "data": {
                        "title": "Talk A",
                        "abstract": "Should not appear without detail_field.",
                        "complete": False,
                    },
                }
            ],
            [{"type": "Checkbox", "field": "complete"}],
        )
        assert "entry-detail" not in html
        assert "Should not appear" not in html

    def test_per_row_document_buttons_respect_visible_if(self):
        from referia.web.render import render_inline_listing

        docs = [
            {
                "n": 0,
                "type": "email",
                "label": "Email feedback",
                "summary": False,
                "visible_if": {"field": "markedFlag", "equals": True},
            }
        ]
        html = render_inline_listing(
            [
                {
                    "index": "ua257",
                    "data": {"title": "Alice", "markedFlag": "yes"},
                },
                {
                    "index": "jrw208",
                    "data": {"title": "Jake", "markedFlag": "no"},
                },
            ],
            [{"type": "Checkbox", "field": "noted", "args": {"description": "Noted"}}],
            documents=docs,
        )
        assert "Email feedback" in html
        assert html.count("Email feedback") == 1
        assert 'id="row-document-actions-ua257"' in html
        assert "hx-vals=" in html
        assert "ua257" in html
        assert 'hx-post="/generate-document/0"' in html
        # Unmarked row keeps a container but skips the gated button.
        assert "Email feedback" not in html.split("jrw208")[-1]

    def test_per_row_document_buttons_without_extra_widgets(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [{"index": "ua257", "data": {"title": "Alice"}}],
            [],
            documents=[{"n": 0, "type": "email", "label": "Email feedback"}],
        )
        assert "entry-extras" in html
        assert "Email feedback" in html
        assert 'id="row-document-actions-ua257"' in html

    def test_populate_all_chrome_and_per_row_button(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "placeholder-report",
                    "data": {
                        "Name": "placeholder-report",
                        "filename": "placeholder.pdf",
                        "units": [
                            {
                                "unit_id": "u1",
                                "word_count": 42,
                                "text": "First paragraph.",
                            }
                        ],
                    },
                }
            ],
            [
                {"type": "precompute", "specifications": []},
                {
                    "type": "PopulateButton",
                    "field": "_segment",
                    "args": {
                        "description": "Segment document",
                        "target": "units",
                    },
                },
                {
                    "type": "Markdown",
                    "field": "filename",
                    "liquid": "**Path**",
                },
            ],
            detail_field="units",
        )
        assert "Segment document all filtered" in html
        assert 'hx-post="/populate-all/_segment"' in html
        assert 'hx-post="/populate/_segment"' in html
        assert "placeholder-report" in html
        assert "placeholder.pdf" in html
        assert "1 paragraph" in html
        assert "First paragraph." in html
        assert 'data-detail-field="units"' in html
        assert "unsupported widget type" not in html
        assert "**Path**" not in html

    def test_name_and_filename_fallbacks_without_title(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "doc-a",
                    "data": {"Name": "Doc A", "filename": "a.pdf"},
                }
            ],
            [],
        )
        assert "Doc A · doc-a" in html
        assert "a.pdf" in html

    def test_extract_embed_all_and_phrase_detail(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "chunk-0",
                    "data": {
                        "Name": "foreword",
                        "filename": "foreword.pdf",
                        "extraction_phrases": [
                            {
                                "kind": "concern",
                                "phrase": "fragmented capital markets",
                                "embedding": [0.1, 0.2],
                            }
                        ],
                    },
                }
            ],
            [
                {
                    "type": "PopulateButton",
                    "field": "_extract",
                    "args": {
                        "description": "Extract",
                        "target": "extraction_payload",
                    },
                },
                {
                    "type": "PopulateButton",
                    "field": "_embed",
                    "args": {
                        "description": "Embed",
                        "target": "extraction_phrases",
                        "requires": "extraction_phrases",
                    },
                },
            ],
            detail_field="extraction_phrases",
        )
        assert "Extract all filtered" in html
        assert "Embed all filtered" in html
        assert 'hx-post="/populate-all/_extract"' in html
        assert 'hx-post="/populate-all/_embed"' in html
        assert "foreword · chunk-0" in html
        assert "1 phrase" in html
        assert "[concern] fragmented capital markets" in html or (
            "[concern]" in html and "fragmented capital markets" in html
        )
        assert "embedded" in html
        assert ">Phrases<" in html
        assert 'data-detail-field="extraction_phrases"' in html
        assert "is-blocked" not in html

    def test_classify_all_and_grounds_detail(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "unit-0",
                    "data": {
                        "filename": "session.docx",
                        "grounds": [
                            {
                                "kind": "benefit",
                                "phrase": "save staff time",
                                "basis": "principle",
                            }
                        ],
                    },
                }
            ],
            [
                {
                    "type": "PopulateButton",
                    "field": "_classify",
                    "args": {
                        "description": "Classify",
                        "target": "grounds_payload",
                    },
                },
            ],
            detail_field="grounds",
        )
        assert "Classify all filtered" in html
        assert 'hx-post="/populate-all/_classify"' in html
        assert "1 point" in html
        assert "[principle]" in html
        assert ">Grounds<" in html

    def test_side_by_side_populate_all_chrome(self):
        from referia.web.render import populate_all_chrome_html

        specs = [
            {"type": "precompute", "specifications": []},
            {
                "type": "Section",
                "title": "Grounds parameters",
                "entries": [
                    {
                        "type": "PopulateButton",
                        "field": "_classify",
                        "args": {
                            "description": "Classify",
                            "all": True,
                            "target": "grounds_payload",
                        },
                    }
                ],
            },
        ]
        html = populate_all_chrome_html(specs, count=2013)
        assert "Classify all filtered" in html
        assert 'hx-post="/populate-all/_classify"' in html
        assert "2013 rows" in html
        assert populate_all_chrome_html(
            [{"type": "PopulateButton", "field": "_x", "args": {}}],
            count=3,
        ) == ""

    def test_embed_blocked_until_extract(self):
        from referia.web.render import render_inline_listing

        specs = [
            {
                "type": "PopulateButton",
                "field": "_extract",
                "args": {
                    "description": "Extract",
                    "target": "extraction_payload",
                },
            },
            {
                "type": "PopulateButton",
                "field": "_embed",
                "args": {
                    "description": "Embed",
                    "target": "extraction_phrases",
                    "requires": "extraction_phrases",
                },
            },
        ]
        empty = render_inline_listing(
            [
                {
                    "index": "chunk-0",
                    "data": {"Name": "foreword", "filename": "foreword.pdf"},
                }
            ],
            specs,
        )
        assert 'hx-post="/populate-all/_extract"' in empty
        assert 'hx-post="/populate/_extract"' in empty
        assert 'hx-post="/populate-all/_embed"' not in empty
        assert 'hx-post="/populate/_embed"' not in empty
        assert "is-blocked" in empty
        assert "Extract all filtered rows first" in empty
        assert "Extract this row first" in empty

        mixed = render_inline_listing(
            [
                {
                    "index": "chunk-0",
                    "data": {
                        "Name": "foreword",
                        "extraction_phrases": [{"kind": "concern", "phrase": "x"}],
                    },
                },
                {
                    "index": "chunk-1",
                    "data": {"Name": "chapter-1"},
                },
            ],
            specs,
        )
        assert 'hx-post="/populate-all/_embed"' not in mixed
        assert mixed.count("is-blocked") >= 2
        assert 'hx-post="/populate/_embed"' in mixed

    def test_listing_chrome_parameters_and_refresh_cache(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "chunk-0",
                    "data": {
                        "Name": "foreword",
                        "phrase_kinds": "concern, benefit, condition",
                        "extract_model": "gpt-4o-mini",
                    },
                }
            ],
            [
                {
                    "type": "Section",
                    "title": "Extract parameters",
                    "entries": [
                        {
                            "type": "HTML",
                            "args": {
                                "value": '<p class="chrome-hint">Extract uses these values.</p>'
                            },
                        },
                        {
                            "type": "Text",
                            "field": "phrase_kinds",
                            "args": {"description": "Phrase kinds"},
                        },
                    ],
                },
                {
                    "type": "Section",
                    "title": "Embed parameters",
                    "entries": [
                        {
                            "type": "Dropdown",
                            "field": "embed_model",
                            "args": {
                                "description": "Embed model",
                                "options": ["text-embedding-3-large"],
                            },
                        },
                    ],
                },
                {
                    "type": "Section",
                    "title": "Cache",
                    "args": {"collapse": False},
                    "entries": [
                        {
                            "type": "PopulateButton",
                            "field": "_refresh_cache",
                            "args": {
                                "description": "Refresh cache",
                                "target": "extraction_payload",
                            },
                        },
                        {
                            "type": "ReloadButton",
                            "field": "_reload",
                            "args": {"description": "Reload cache"},
                        },
                    ],
                },
                {
                    "type": "PopulateButton",
                    "field": "_extract",
                    "args": {"description": "Extract", "target": "extraction_payload"},
                },
            ],
        )
        assert "Extract parameters" in html
        assert "Embed parameters" in html
        assert "<h3>Cache</h3>" in html
        assert 'id="listing-chrome-form"' in html
        assert 'hx-post="/field-bulk/phrase_kinds"' in html
        assert 'hx-post="/field-bulk/embed_model"' in html
        assert 'hx-post="/populate-all/_refresh_cache"' in html
        assert "Refresh cache" in html
        assert 'hx-post="/reload"' in html
        assert "Reload cache" in html
        assert 'class="review-section review-section-static"' in html
        assert "<summary>Cache</summary>" not in html
        assert 'hx-post="/populate-all/_extract"' in html

    def test_textarea_extra_is_collapsed(self):
        from referia.web.render import render_inline_listing

        html = render_inline_listing(
            [
                {
                    "index": "doc-a",
                    "data": {
                        "title": "Doc A",
                        "notes": "A catalog remark.",
                    },
                }
            ],
            [
                {
                    "type": "Textarea",
                    "field": "notes",
                    "args": {"description": "Catalog notes"},
                }
            ],
        )
        assert 'class="entry-detail entry-extra-collapse"' in html
        assert "<summary>Catalog notes</summary>" in html
        assert "A catalog remark." in html
        assert 'name="notes"' in html
        # Inner widget label is omitted; the summary is the label.
        assert "widget-description" not in html

    def test_listing_helper_title_detail_and_requires(self):
        from referia.web.render import (
            _htmx_field_attrs,
            _listing_chrome_ctx,
            _listing_detail_noun,
            _listing_detail_text,
            _listing_row_description,
            _listing_row_title,
            _populate_requires_field,
            _requires_satisfied,
            _section_collapsible,
            render_inline_listing,
        )

        assert _listing_row_title({"title": "Alpha"}, "idx") == "Alpha"
        assert _listing_row_title({"Name": "same"}, "same") == "same"
        assert _listing_row_title({}, "idx") == "idx"
        assert _listing_detail_noun("units") == "paragraph"
        assert _listing_detail_noun("extraction_phrases") == "phrase"
        assert _listing_detail_noun("notes") == "item"
        assert _listing_row_description({"filename": "a.pdf"}) == "a.pdf"
        assert _listing_row_description(
            {"units": [{}, {}]}, detail_field="units"
        ) == "2 paragraphs"
        assert _listing_detail_text(None) == ""
        assert _listing_detail_text([]) == ""
        assert _listing_detail_text(["one", "two"]) == "one\ntwo"
        assert "embedded" not in _listing_detail_text(
            [{"kind": "benefit", "phrase": "markets"}]
        )
        assert "body text" in _listing_detail_text(
            [{"id": "u1", "body": "body text"}]
        )
        assert _listing_detail_text("plain") == "plain"
        assert _requires_satisfied(None) is False
        assert _requires_satisfied([]) is True
        assert _requires_satisfied({}) is True
        assert _requires_satisfied("  ") is False
        assert _requires_satisfied("ok") is True
        assert _requires_satisfied(False) is False
        assert _requires_satisfied(True) is True
        assert _requires_satisfied(float("nan")) is False
        assert _requires_satisfied(0) is False
        assert _populate_requires_field({"requires": "extraction_phrases"}) == (
            "extraction_phrases"
        )
        assert _populate_requires_field({"args": {"requires": False}}) == ""
        assert _section_collapsible({"args": {"collapse": False}}) is False
        assert _section_collapsible({"args": {"collapsible": False}}) is False
        assert _section_collapsible({}) is True
        token = _listing_chrome_ctx.set(True)
        try:
            assert 'hx-post="/field-bulk/phrase_kinds"' in _htmx_field_attrs(
                "phrase_kinds"
            )
        finally:
            _listing_chrome_ctx.reset(token)
        empty = render_inline_listing(
            [],
            [
                {
                    "type": "Section",
                    "title": "Cache",
                    "args": {"collapse": False},
                    "entries": [
                        {
                            "type": "ReloadButton",
                            "field": "_reload",
                            "args": {"description": "Reload cache"},
                        }
                    ],
                }
            ],
        )
        assert "listing-chrome" in empty
        assert "No rows match the current filters." in empty
        assert "review-section-static" in empty
