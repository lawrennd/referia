"""Unit tests for referia.web.render — widget-to-HTML renderer.

Covers render_widget() for every supported widget type, render_viewer(),
render_form(), visible_if conditions, and HTML escaping.
"""

import pytest
from referia.web.render import render_widget, render_viewer, render_form


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

    def test_populate_button_indicator_targets_target_field(self):
        """hx-indicator should point to the target field's widget container."""
        html = render_widget({"type": "PopulateButton", "field": "summary", "args": {}})
        assert 'hx-indicator="#widget-summary"' in html

    def test_populate_button_indicator_uses_args_target_when_present(self):
        """Complex format: args.target is the populate target; URL and indicator use it."""
        html = render_widget({
            "type": "PopulateButton",
            "field": "populate_btn",
            "args": {"target": "notes"},
        })
        # URL and indicator must both use the args.target, not the button's own field.
        assert 'hx-post="/populate/notes"' in html
        assert 'hx-indicator="#widget-notes"' in html

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
