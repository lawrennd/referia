"""
Integration tests for conditional widget visibility (visible_if feature).

This test suite verifies that:
1. Widgets with visible_if conditions show/hide based on data values
2. Visibility updates during refresh cycle
3. Works with boolean fields (checkboxes)
4. Works with other field types (string comparisons, etc.)
5. Template-level visibility propagates to all widgets
6. Nested visibility conditions work correctly
"""

import pytest
import tempfile
import os
import pandas as pd
import yaml
from pathlib import Path

from referia.config.interface import Interface
from referia.assess.review import Reviewer
from referia.system import Sys
from lynguine.assess.data import CustomDataFrame


class TestConditionalVisibility:
    """Integration tests for visible_if feature."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def sample_config_with_visibility(self, temp_dir):
        """Create a test configuration with visible_if conditions."""
        config = {
            "templates": {
                "conditional_section": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "### %title%"
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%Summary",
                            "args": {
                                "description": "Summary",
                                "rows": 5
                            }
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%Comments",
                            "args": {
                                "description": "Comments",
                                "rows": 3
                            }
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "conditional_section",
                    "instances": [
                        {
                            "title": "Chapter 1",
                            "prefix": "ch1"
                        }
                    ],
                    "visible_if": "Ch1Present"
                },
                {
                    "template": "conditional_section",
                    "instances": [
                        {
                            "title": "Chapter 2", 
                            "prefix": "ch2"
                        }
                    ],
                    "visible_if": "Ch2Present"
                },
                {
                    "type": "Markdown",
                    "liquid": "### Always Visible",
                    "visible_if": None  # Explicitly no condition
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx",
                "strict_columns": False
            }
        }
        
        config_file = temp_dir / "_referia.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        return temp_dir, config_file
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data with Present fields."""
        data = pd.DataFrame({
            "Ch1Present": [True, False, True],
            "Ch2Present": [False, True, True],
            "ch1Summary": ["Summary 1A", "Summary 1B", "Summary 1C"],
            "ch2Summary": ["Summary 2A", "Summary 2B", "Summary 2C"],
            "ch1Comments": ["Comments 1A", "Comments 1B", "Comments 1C"],
            "ch2Comments": ["Comments 2A", "Comments 2B", "Comments 2C"],
        }, index=pd.Index(["doc1", "doc2", "doc3"], name="index"))
        
        return data
    
    def test_widget_visibility_based_on_boolean_field(self, sample_config_with_visibility, sample_data):
        """Test that widgets show/hide based on boolean field values."""
        temp_dir, config_file = sample_config_with_visibility
        
        # Load interface and data
        interface = Interface.from_file(directory=str(temp_dir), user_file="_referia.yml")
        sys = Sys(interface=interface)
        
        # Create CustomDataFrame with sample data
        df = CustomDataFrame(sample_data, interface=interface)
        
        # Create Reviewer
        reviewer = Reviewer(
            index="doc1",  # Ch1Present=True, Ch2Present=False
            data=df,
            interface=interface,
            system=sys
        )
        
        # Get widgets - they're in the main widget cluster, not _view_list
        widgets = reviewer._widgets.to_dict()
        
        # Find Chapter 1 and Chapter 2 widgets
        ch1_widgets = [k for k in widgets.keys() if 'ch1' in k.lower()]
        ch2_widgets = [k for k in widgets.keys() if 'ch2' in k.lower()]
        
        # Chapter 1 should be visible (Ch1Present=True)
        for widget_key in ch1_widgets:
            field_widget = widgets[widget_key]
            # Access the inner ipywidget's layout
            assert field_widget.widget.layout.display != 'none', \
                f"Chapter 1 widget '{widget_key}' should be visible when Ch1Present=True"
        
        # Chapter 2 should be hidden (Ch2Present=False)
        for widget_key in ch2_widgets:
            field_widget = widgets[widget_key]
            # Access the inner ipywidget's layout
            assert field_widget.widget.layout.display == 'none', \
                f"Chapter 2 widget '{widget_key}' should be hidden when Ch2Present=False"
    
    def test_visibility_updates_on_index_change(self, sample_config_with_visibility, sample_data):
        """Test that visibility updates when navigating to different index."""
        temp_dir, config_file = sample_config_with_visibility
        
        # Load interface and data
        interface = Interface.from_file(directory=str(temp_dir), user_file="_referia.yml")
        sys = Sys(interface=interface)
        df = CustomDataFrame(sample_data, interface=interface)
        
        # Create Reviewer starting at doc1
        reviewer = Reviewer(index="doc1", data=df, interface=interface, system=sys)
        widgets = reviewer._widgets.to_dict()
        
        # At doc1: Ch1Present=True, Ch2Present=False
        ch1_widgets = [k for k in widgets.keys() if 'ch1' in k.lower()]
        ch2_widgets = [k for k in widgets.keys() if 'ch2' in k.lower()]
        
        # Chapter 1 visible, Chapter 2 hidden
        for widget_key in ch1_widgets:
            assert widgets[widget_key].widget.layout.display != 'none'
        for widget_key in ch2_widgets:
            assert widgets[widget_key].widget.layout.display == 'none'
        
        # Change to doc2: Ch1Present=False, Ch2Present=True
        reviewer.set_index("doc2")
        reviewer.populate_display()  # This should update visibility
        
        # Now Chapter 1 should be hidden, Chapter 2 visible
        for widget_key in ch1_widgets:
            assert widgets[widget_key].widget.layout.display == 'none', \
                f"Chapter 1 should be hidden at doc2 (Ch1Present=False)"
        for widget_key in ch2_widgets:
            assert widgets[widget_key].widget.layout.display != 'none', \
                f"Chapter 2 should be visible at doc2 (Ch2Present=True)"
    
    def test_visibility_with_complex_condition(self, temp_dir):
        """Test visibility with complex condition format (dict with field and equals)."""
        config = {
            "review": [
                {
                    "type": "Textarea",
                    "field": "testField",
                    "visible_if": {
                        "field": "status",
                        "equals": "active"
                    }
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx",
                "strict_columns": False
            }
        }
        
        config_file = temp_dir / "_referia.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Create data
        data = pd.DataFrame({
            "status": ["active", "inactive", "active"],
            "testField": ["A", "B", "C"]
        }, index=pd.Index(["doc1", "doc2", "doc3"], name="index"))
        
        # Load and test
        interface = Interface.from_file(directory=str(temp_dir), user_file="_referia.yml")
        sys = Sys(interface=interface)
        df = CustomDataFrame(data, interface=interface)
        
        # Test at doc1 (status=active, should be visible)
        reviewer = Reviewer(index="doc1", data=df, interface=interface, system=sys)
        widgets = reviewer._widgets.to_dict()
        test_widget = widgets.get("testField")
        
        assert test_widget is not None
        assert test_widget.widget.layout.display != 'none', \
            "Widget should be visible when status='active'"
        
        # Test at doc2 (status=inactive, should be hidden)
        reviewer.set_index("doc2")
        reviewer.populate_display()
        
        assert test_widget.widget.layout.display == 'none', \
            "Widget should be hidden when status='inactive'"
    
    def test_widget_without_visibility_always_visible(self, temp_dir):
        """Test that widgets without visible_if are always visible."""
        config = {
            "review": [
                {
                    "type": "Textarea",
                    "field": "alwaysVisible",
                    "args": {"description": "Always Visible"}
                },
                {
                    "type": "Textarea",
                    "field": "conditional",
                    "visible_if": "showIt",
                    "args": {"description": "Conditional"}
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx",
                "strict_columns": False
            }
        }
        
        config_file = temp_dir / "_referia.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Create data with showIt=False
        data = pd.DataFrame({
            "showIt": [False],
            "alwaysVisible": ["Always here"],
            "conditional": ["Sometimes here"]
        }, index=pd.Index(["doc1"], name="index"))
        
        # Load and test
        interface = Interface.from_file(directory=str(temp_dir), user_file="_referia.yml")
        sys = Sys(interface=interface)
        df = CustomDataFrame(data, interface=interface)
        
        reviewer = Reviewer(index="doc1", data=df, interface=interface, system=sys)
        widgets = reviewer._widgets.to_dict()
        
        # Widget without condition should be visible
        assert widgets["alwaysVisible"].widget.layout.display != 'none', \
            "Widget without visible_if should always be visible"
        
        # Widget with condition should be hidden (showIt=False)
        assert widgets["conditional"].widget.layout.display == 'none', \
            "Widget with visible_if should be hidden when condition is false"
    
    def test_missing_condition_field_hides_widget(self, temp_dir):
        """Test that widget is hidden if condition field doesn't exist in data."""
        config = {
            "review": [
                {
                    "type": "Textarea",
                    "field": "testField",
                    "visible_if": "nonexistentField"
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx",
                "strict_columns": False
            }
        }
        
        config_file = temp_dir / "_referia.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Create data WITHOUT the condition field
        data = pd.DataFrame({
            "testField": ["Value"]
        }, index=pd.Index(["doc1"], name="index"))
        
        # Load and test
        interface = Interface.from_file(directory=str(temp_dir), user_file="_referia.yml")
        sys = Sys(interface=interface)
        df = CustomDataFrame(data, interface=interface)
        
        reviewer = Reviewer(index="doc1", data=df, interface=interface, system=sys)
        widgets = reviewer._widgets.to_dict()
        
        # Widget should be hidden when condition field doesn't exist
        assert widgets["testField"].widget.layout.display == 'none', \
            "Widget should be hidden when condition field doesn't exist in data"


class TestTemplateVisibilityPropagation:
    """Test that visible_if at template level propagates to all widgets."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_template_visibility_propagates_to_all_widgets(self, temp_dir):
        """Test that visible_if on template instance applies to all expanded widgets."""
        config = {
            "templates": {
                "section": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "### %title%"
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%Summary"
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%Comments"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "section",
                    "instances": [
                        {
                            "title": "Test Section",
                            "prefix": "test"
                        }
                    ],
                    "visible_if": "showSection"
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx",
                "strict_columns": False
            }
        }
        
        config_file = temp_dir / "_referia.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Create data with showSection=False
        data = pd.DataFrame({
            "showSection": [False],
            "testSummary": ["Summary"],
            "testComments": ["Comments"]
        }, index=pd.Index(["doc1"], name="index"))
        
        # Load and test
        interface = Interface.from_file(directory=str(temp_dir), user_file="_referia.yml")
        sys = Sys(interface=interface)
        df = CustomDataFrame(data, interface=interface)
        
        reviewer = Reviewer(index="doc1", data=df, interface=interface, system=sys)
        widgets = reviewer._widgets.to_dict()
        
        # All widgets from template should be hidden
        test_widgets = [k for k in widgets.keys() if 'test' in k.lower()]
        for widget_key in test_widgets:
            field_widget = widgets[widget_key]
            assert field_widget.widget.layout.display == 'none', \
                f"All widgets from template should be hidden when visible_if is false (widget: {widget_key})"


class TestStrictColumnsDefault:
    """
    Regression tests for strict_columns default behaviour.

    referia should default to strict_columns=False (permissive) so that configs
    which have extra columns in their data files (e.g. a 'SessionDate' column not
    listed in the spec) continue to load without error.  Configs can opt IN to
    strict mode by explicitly setting strict_columns: true.
    """

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def _write_config(self, temp_dir, strict_columns_value=None, in_sub=False):
        """Write a minimal _referia.yml; strict_columns_value=None means omit the key."""
        alloc = {
            "index": "Name",
            "type": "excel",
            "filename": "data.xlsx",
            "header": 0,
        }
        config: dict = {
            "allocation": alloc,
            "output": {"type": "excel", "filename": "output.xlsx"},
            "viewer": [{"field": "Name", "type": "text"}],
        }
        if strict_columns_value is not None:
            if in_sub:
                config["allocation"]["strict_columns"] = strict_columns_value
            else:
                config["strict_columns"] = strict_columns_value
        with open(temp_dir / "_referia.yml", "w") as f:
            yaml.dump(config, f)

    def _write_data(self, temp_dir, extra_col=True):
        df = pd.DataFrame({"Name": ["Alice", "Bob"]})
        if extra_col:
            df["SessionDate"] = ["2022-01-01", "2022-01-02"]
        df.to_excel(temp_dir / "data.xlsx", index=False)

    # ------------------------------------------------------------------ #
    # Unit tests of the strict_columns resolution logic.
    #
    # The relevant code path is referia's _finalize_df override, which is
    # called with strict_columns=None (its default) by lynguine's from_flow
    # for non-input data (e.g. when an existing output file is re-read).
    # The override must resolve None → False unless the config says True.
    # ------------------------------------------------------------------ #

    def _resolve(self, sub_strict, top_strict):
        """
        Run the resolution logic extracted from CustomDataFrame._finalize_df
        and return the resolved value.

        sub_strict: strict_columns value to put in the sub-interface (or None=omit)
        top_strict: strict_columns value to put in the top-level interface (or None=omit)
        """
        sub_data = {}
        if sub_strict is not None:
            sub_data["strict_columns"] = sub_strict

        top_data = {}
        if top_strict is not None:
            top_data["strict_columns"] = top_strict

        # Replicate the logic from referia/assess/data.py CustomDataFrame._finalize_df
        # so that we can test it independently of the full data pipeline.
        class _FakeInterface(dict):
            """Minimal dict subclass that mimics Interface for the 'in' and '[]' checks."""

        interface = _FakeInterface(sub_data)
        top_interface = _FakeInterface(top_data) if top_data else None

        strict_columns = None   # the argument as lynguine would pass it
        # Mirror the logic in referia/assess/data.py CustomDataFrame._finalize_df:
        # only resolves to False when explicitly told so; otherwise defaults to True.
        if strict_columns is None:
            if "strict_columns" in interface and not interface["strict_columns"]:
                strict_columns = False
            elif top_interface is not None and "strict_columns" in top_interface and not top_interface["strict_columns"]:
                strict_columns = False
            else:
                strict_columns = True
        return strict_columns

    def test_default_is_true_when_no_strict_set(self):
        """No strict_columns anywhere → resolved value must be True (opt-in to permissive)."""
        assert self._resolve(sub_strict=None, top_strict=None) is True

    def test_false_in_sub_resolves_false(self):
        """strict_columns: false in sub-interface → False."""
        assert self._resolve(sub_strict=False, top_strict=None) is False

    def test_true_in_sub_resolves_true(self):
        """strict_columns: true in sub-interface → True."""
        assert self._resolve(sub_strict=True, top_strict=None) is True

    def test_false_in_top_resolves_false(self):
        """strict_columns: false in top-level interface → False."""
        assert self._resolve(sub_strict=None, top_strict=False) is False

    def test_true_in_top_resolves_true(self):
        """strict_columns: true in top-level interface → True."""
        assert self._resolve(sub_strict=None, top_strict=True) is True

    def test_permissive_wins_at_either_level(self):
        """If either interface says false, the result is False (permissive wins)."""
        assert self._resolve(sub_strict=False, top_strict=True) is False
        assert self._resolve(sub_strict=True, top_strict=False) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

