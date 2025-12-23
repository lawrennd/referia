"""
Tests for CIP-0006 template expansion system.

This test suite verifies that:
1. Template parameter substitution works correctly with %param% syntax
2. Liquid template syntax {{field}} is preserved through substitution
3. Template-expanded fields are correctly extracted and added to output columns
4. _modified and _created timestamp columns are auto-generated for all fields
"""

import pytest
import tempfile
import os
from referia.config.interface import Interface


class TestTemplateParameterSubstitution:
    """Test template parameter substitution with %param% syntax."""
    
    def test_single_brace_substitution(self):
        """Test that %param% is substituted with parameter values."""
        from referia.config.interface import Interface
        
        config = {
            "templates": {
                "test_template": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "### %title%"
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%Summary"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "test_template",
                    "instances": [
                        {"title": "Chapter 1", "prefix": "ch1"},
                        {"title": "Chapter 2", "prefix": "ch2"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        
        # Check that templates were expanded
        review = interface._config['review']
        assert len(review) == 4  # 2 instances × 2 widgets each
        
        # Check first instance
        assert review[0]['liquid'] == "### Chapter 1"
        assert review[1]['field'] == "ch1Summary"
        
        # Check second instance
        assert review[2]['liquid'] == "### Chapter 2"
        assert review[3]['field'] == "ch2Summary"
    
    def test_liquid_syntax_preserved(self):
        """Test that {{field}} syntax is NOT substituted (preserved for Liquid)."""
        config = {
            "templates": {
                "test_template": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "### %title% by {{givenName}}"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "test_template",
                    "instances": [
                        {"title": "Abstract"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        review = interface._config['review']
        
        # %title% should be substituted, {{givenName}} should remain
        assert review[0]['liquid'] == "### Abstract by {{givenName}}"
    
    def test_display_syntax_substituted(self):
        """Test that {Name} in display fields gets proper substitution."""
        config = {
            "templates": {
                "test_template": {
                    "pattern": [
                        {
                            "type": "PopulateButton",
                            "args": {
                                "compute": {
                                    "view_args": {
                                        "filename": {
                                            "display": "{Name}_thesis_%pdf_name%.pdf"
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "test_template",
                    "instances": [
                        {"pdf_name": "abstract", "Name": "{Name}"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        review = interface._config['review']
        
        # %pdf_name% substituted, {Name} preserved for display processing
        display = review[0]['args']['compute']['view_args']['filename']['display']
        assert display == "{Name}_thesis_abstract.pdf"


class TestOutputColumnGeneration:
    """Test automatic output column generation from template-expanded fields."""
    
    def test_columns_auto_generated_from_review_fields(self):
        """Test that output columns are auto-generated when not specified."""
        config = {
            "templates": {
                "simple": {
                    "pattern": [
                        {
                            "type": "Textarea",
                            "field": "%prefix%Summary"
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%Details"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "simple",
                    "instances": [
                        {"prefix": "ch1"},
                        {"prefix": "ch2"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        
        # Check that columns were auto-generated
        assert "columns" in interface._data['output']
        columns = interface._data['output']['columns']
        
        # Should have the base fields
        assert "ch1Summary" in columns
        assert "ch1Details" in columns
        assert "ch2Summary" in columns
        assert "ch2Details" in columns
    
    def test_modified_created_columns_added(self):
        """Test that _modified and _created columns are auto-added."""
        config = {
            "review": [
                {
                    "type": "Textarea",
                    "field": "testField"
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        columns = interface._data['output']['columns']
        
        # Should have base field plus timestamp columns
        assert "testField" in columns
        assert "testField_modified" in columns
        assert "testField_created" in columns
    
    def test_explicit_columns_get_timestamps(self):
        """Test that explicitly listed columns also get _modified/_created."""
        config = {
            "review": [
                {
                    "type": "Textarea",
                    "field": "myField"
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx",
                "columns": ["myField", "otherField"]
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        columns = interface._data['output']['columns']
        
        # Original columns should remain
        assert "myField" in columns
        assert "otherField" in columns
        
        # Timestamp columns should be added for review field
        assert "myField_modified" in columns
        assert "myField_created" in columns
    
    def test_many_template_instances_all_included(self):
        """Test that many template instances all get their columns generated."""
        config = {
            "templates": {
                "chapter": {
                    "pattern": [
                        {
                            "type": "Textarea",
                            "field": "%prefix%Summary"
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%Questions"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "chapter",
                    "instances": [
                        {"prefix": f"ch{i}"} for i in range(1, 13)  # 12 chapters
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        columns = interface._data['output']['columns']
        
        # All 12 chapters should have their fields
        for i in range(1, 13):
            assert f"ch{i}Summary" in columns
            assert f"ch{i}Questions" in columns
            assert f"ch{i}Summary_modified" in columns
            assert f"ch{i}Questions_modified" in columns


class TestNestedTemplates:
    """Test nested/recursive template expansion."""
    
    def test_single_level_nesting(self):
        """Test basic one-level template nesting."""
        config = {
            "templates": {
                "comment_section": {
                    "pattern": [
                        {
                            "type": "Textarea",
                            "field": "%prefix%Comments"
                        },
                        {
                            "type": "PopulateButton",
                            "args": {
                                "target": "%prefix%Comments"
                            }
                        }
                    ]
                },
                "chapter_review": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "### %title%"
                        },
                        {
                            "template": "comment_section",
                            "instances": [
                                {"prefix": "%prefix%General"}
                            ]
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "chapter_review",
                    "instances": [
                        {"title": "Chapter 1", "prefix": "ch1"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        review = interface._config['review']
        
        # Should have markdown + textarea + button
        assert len(review) == 3
        assert review[0]['liquid'] == "### Chapter 1"
        assert review[1]['field'] == "ch1GeneralComments"
        assert review[2]['args']['target'] == "ch1GeneralComments"
    
    def test_multiple_level_nesting(self):
        """Test multiple levels of template nesting."""
        config = {
            "templates": {
                "base_field": {
                    "pattern": [
                        {
                            "type": "Textarea",
                            "field": "%field_name%"
                        }
                    ]
                },
                "field_with_button": {
                    "pattern": [
                        {
                            "template": "base_field",
                            "instances": [
                                {"field_name": "%prefix%Field"}
                            ]
                        },
                        {
                            "type": "PopulateButton",
                            "args": {
                                "target": "%prefix%Field"
                            }
                        }
                    ]
                },
                "section": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "### %title%"
                        },
                        {
                            "template": "field_with_button",
                            "instances": [
                                {"prefix": "%prefix%"}
                            ]
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "section",
                    "instances": [
                        {"title": "Results", "prefix": "results"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        review = interface._config['review']
        
        # Should have markdown + textarea + button (3 levels deep)
        assert len(review) == 3
        assert review[0]['liquid'] == "### Results"
        assert review[1]['field'] == "resultsField"
        assert review[2]['args']['target'] == "resultsField"
    
    def test_circular_reference_detection(self):
        """Test that circular template references are detected."""
        config = {
            "templates": {
                "template_a": {
                    "pattern": [
                        {
                            "template": "template_b",
                            "instances": [{"param": "value"}]
                        }
                    ]
                },
                "template_b": {
                    "pattern": [
                        {
                            "template": "template_a",
                            "instances": [{"param": "value"}]
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "template_a",
                    "instances": [{"param": "value"}]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            Interface(data=config, directory="/tmp", user_file="test.yml")
        
        assert "Circular template reference" in str(exc_info.value)
        assert "template_a" in str(exc_info.value)
        assert "template_b" in str(exc_info.value)
    
    def test_max_depth_exceeded(self):
        """Test that maximum nesting depth is enforced."""
        # Create a chain of templates that exceed max depth
        templates = {}
        for i in range(15):
            if i == 14:
                # Last template has actual content
                templates[f"level_{i}"] = {
                    "pattern": [
                        {"type": "Markdown", "liquid": "Done"}
                    ]
                }
            else:
                # Each template references the next
                templates[f"level_{i}"] = {
                    "pattern": [
                        {
                            "template": f"level_{i+1}",
                            "instances": [{}]
                        }
                    ]
                }
        
        config = {
            "templates": templates,
            "review": [
                {
                    "template": "level_0",
                    "instances": [{}]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            Interface(data=config, directory="/tmp", user_file="test.yml")
        
        assert "Maximum template nesting depth" in str(exc_info.value)
    
    def test_multiple_nested_instances(self):
        """Test multiple instances at nested levels."""
        config = {
            "templates": {
                "item": {
                    "pattern": [
                        {
                            "type": "Textarea",
                            "field": "%name%"
                        }
                    ]
                },
                "section": {
                    "pattern": [
                        {
                            "template": "item",
                            "instances": [
                                {"name": "%prefix%A"},
                                {"name": "%prefix%B"}
                            ]
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "section",
                    "instances": [
                        {"prefix": "ch1"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        review = interface._config['review']
        
        # Should expand to 2 textareas
        assert len(review) == 2
        assert review[0]['field'] == "ch1A"
        assert review[1]['field'] == "ch1B"


class TestTemplateEscaping:
    """Test escaping of literal percent signs."""
    
    def test_double_percent_becomes_literal(self):
        """Test that %% is converted to literal % (Windows batch convention)."""
        config = {
            "templates": {
                "test": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "Success rate: 95%% for %title%"
                        },
                        {
                            "type": "Textarea",
                            "field": "%prefix%_100%%_complete"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "test",
                    "instances": [
                        {"title": "Chapter 1", "prefix": "ch1"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        review = interface._config['review']
        
        # %% should become %, %title% should be substituted
        assert review[0]['liquid'] == "Success rate: 95% for Chapter 1"
        # %% in field names should also become %
        assert review[1]['field'] == "ch1_100%_complete"
    
    def test_multiple_percent_escapes(self):
        """Test multiple %% escapes in same string."""
        config = {
            "templates": {
                "test": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "Values: 10%%, 20%%, 30%% in %section%"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "test",
                    "instances": [
                        {"section": "Results"}
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        review = interface._config['review']
        
        # All %% should become %
        assert review[0]['liquid'] == "Values: 10%, 20%, 30% in Results"


class TestTemplateErrors:
    """Test error handling in template expansion."""
    
    def test_missing_required_parameter(self):
        """Test that missing required parameters raise clear errors."""
        config = {
            "templates": {
                "test": {
                    "pattern": [
                        {
                            "type": "Markdown",
                            "liquid": "### %title%"
                        }
                    ]
                }
            },
            "review": [
                {
                    "template": "test",
                    "instances": [
                        {"prefix": "ch1"}  # Missing 'title' parameter
                    ]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            Interface(data=config)
        
        assert "title" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()
    
    def test_undefined_template(self):
        """Test that referencing undefined templates is handled gracefully."""
        # Note: Currently undefined templates don't raise errors during init
        # This test documents the current behavior - it creates empty review
        config = {
            "review": [
                {
                    "template": "nonexistent",
                    "instances": [{"param": "value"}]
                }
            ],
            "output": {
                "type": "excel",
                "filename": "test.xlsx"
            }
        }
        
        interface = Interface(data=config, directory="/tmp", user_file="test.yml")
        
        # Template expansion should have failed, resulting in empty review
        # (or the template reference is just passed through)
        # This test documents current behavior, not necessarily desired behavior
        assert interface._config is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

