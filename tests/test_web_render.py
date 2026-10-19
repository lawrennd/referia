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

    def test_static_image_viewer(self):
        html = render_viewer(
            {"type": "StaticImage"},
            "https://example.com/a.png",
            viewer_index=1,
        )
        assert 'class="viewer viewer-image"' in html
        assert 'src="https://example.com/a.png"' in html


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
        assert 'name="filter__title__query"' in bar
        assert 'value="admissions"' in bar
        assert 'name="filter__title__mode"' in bar
        assert 'value="words" selected' in bar

        bar_ver = render_filter_bar([], [], {"_group": "version"})
        assert 'value="version" selected' in bar_ver

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
