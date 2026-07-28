"""
Test coverage for template expansion integration.

These tests follow Test-Driven Development (TDD) approach:
1. Write failing test (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor while keeping tests green

This module tests full integration of template expansion, ensuring
templates work correctly with the full referia/lynguine pipeline.

Created as part of backlog item: 2025-12-22_implement-template-expansion.md
Related CIP: 0006 (Configuration Template Expansion System)
"""

import pytest
import tempfile
import os
import yaml
from referia.config.interface import Interface

# CIP-0006 template expansion is not yet implemented — mark all tests as expected failures
pytestmark = pytest.mark.xfail(
    reason="TDD: CIP-0006 template expansion not yet implemented",
    strict=False
)


class TestFullConfigExpansion:
    """Test complete configuration expansion with templates."""
    
    def test_multiple_templates_in_config(self):
        """
        Test using multiple different templates in one configuration.
        
        Expected behavior: Multiple templates can be used and expanded
        independently in the same config.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'chapter_template': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Summary'},
                        {'type': 'Textarea', 'field': '{prefix}Questions'}
                    ]
                },
                'section_template': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Notes'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'chapter_template',
                    'instances': [
                        {'prefix': 'ch1'},
                        {'prefix': 'ch2'}
                    ]
                },
                {
                    'template': 'section_template',
                    'instances': [
                        {'prefix': 'prologue'},
                        {'prefix': 'epilogue'}
                    ]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'id',
                'data': {'id': ['test'], 'name': ['Test']}
            }
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            review = interface._config['review']
            
            # Should have 6 total entries: 
            # - ch1Summary, ch1Questions
            # - ch2Summary, ch2Questions
            # - prologueNotes
            # - epilogueNotes
            fields = [e.get('field') for e in review if 'field' in e]
            
            assert 'ch1Summary' in fields
            assert 'ch1Questions' in fields
            assert 'ch2Summary' in fields
            assert 'ch2Questions' in fields
            assert 'prologueNotes' in fields
            assert 'epilogueNotes' in fields
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_mixed_templates_and_explicit_entries(self):
        """
        Test mixing template entries with explicit review entries.
        
        Expected behavior: Can have both template references and
        explicit entries in same review section.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'simple_template': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Comment'}
                    ]
                }
            },
            'review': [
                # Explicit entry before template
                {
                    'type': 'Markdown',
                    'liquid': '## Introduction'
                },
                # Template reference
                {
                    'template': 'simple_template',
                    'instances': [{'prefix': 'ch1'}]
                },
                # Explicit entry after template
                {
                    'type': 'Textarea',
                    'field': 'ExplicitField'
                }
            ],
            'input': {
                'type': 'local',
                'index': 'id',
                'data': {'id': ['test'], 'name': ['Test']}
            }
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            review = interface._config['review']
            
            # Should have 3 entries in order
            assert len(review) == 3
            
            # Check order is preserved
            assert review[0]['type'] == 'Markdown'
            assert review[0]['liquid'] == '## Introduction'
            
            assert review[1]['type'] == 'Textarea'
            assert review[1]['field'] == 'ch1Comment'
            
            assert review[2]['type'] == 'Textarea'
            assert review[2]['field'] == 'ExplicitField'
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_external_template_with_multiple_instances(self):
        """
        Test external template file with many instances.
        
        Expected behavior: External template can be reused many times.
        
        TDD Status: RED - This test should fail initially
        """
        tmpdir = tempfile.mkdtemp()
        try:
            # Create external template file
            template_file = f"{tmpdir}/chapter_review_template.yml"
            template_content = {
                'pattern': [
                    {'type': 'Textarea', 'field': '{prefix}Summary', 'args': {'rows': 10}},
                    {'type': 'Textarea', 'field': '{prefix}Questions', 'args': {'rows': 5}},
                    {'type': 'Textarea', 'field': '{prefix}CustomQuery', 'args': {'rows': 3}}
                ]
            }
            with open(template_file, 'w') as f:
                yaml.dump(template_content, f)
            
            # Create config using external template multiple times
            config = {
                'templates': {
                    'chapter_review': {
                        'file': './chapter_review_template.yml'
                    }
                },
                'review': [
                    {
                        'template': 'chapter_review',
                        'instances': [
                            {'prefix': f'ch{i}'}
                            for i in range(1, 6)  # ch1 through ch5
                        ]
                    }
                ],
                'input': {
                    'type': 'local',
                    'index': 'id',
                    'data': {'id': ['test'], 'name': ['Test']}
                }
            }
            
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            review = interface._config['review']
            
            # Should have 15 entries (5 chapters × 3 fields each)
            assert len(review) == 15
            
            # Check all chapters are present
            fields = [e.get('field') for e in review]
            for i in range(1, 6):
                assert f'ch{i}Summary' in fields
                assert f'ch{i}Questions' in fields
                assert f'ch{i}CustomQuery' in fields
            
        finally:
            if os.path.exists(template_file):
                os.remove(template_file)
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


class TestIntegrationWithLynguine:
    """Test that expanded templates work correctly with lynguine."""
    
    def test_expanded_config_passes_to_lynguine(self):
        """
        Test that expanded config is valid for lynguine.
        
        Expected behavior: After template expansion, config should
        be valid lynguine configuration.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'field_template': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Field'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'field_template',
                    'instances': [{'prefix': 'test'}]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'id',
                'data': {'id': ['row1'], 'value': ['data1']}
            }
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            # This should not raise any errors
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            # Interface should be created successfully
            assert interface is not None
            
            # Should be able to access interface functionality (inherited from lynguine)
            # Check that it has the expected lynguine.config.interface.Interface methods
            assert hasattr(interface, '__getitem__')
            assert hasattr(interface, '__setitem__')
            assert hasattr(interface, 'keys')
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_no_template_artifacts_in_final_config(self):
        """
        Test that no template artifacts remain after expansion.
        
        Expected behavior: Final config should not contain 'template',
        'instances' keys or {placeholder} strings.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'simple': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Data'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'simple',
                    'instances': [{'prefix': 'test'}]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'id',
                'data': {'id': ['test'], 'name': ['Test']}
            }
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            review = interface._config['review']
            
            # No entries should have 'template' or 'instances' keys
            for entry in review:
                assert 'template' not in entry, \
                    "Expanded review should not contain 'template' key"
                assert 'instances' not in entry, \
                    "Expanded review should not contain 'instances' key"
                
                # No string values should contain unsubstituted placeholders
                self._check_no_placeholders(entry)
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def _check_no_placeholders(self, obj):
        """Recursively check object has no {placeholder} strings."""
        import re
        
        if isinstance(obj, str):
            # Check for any {word} patterns
            placeholders = re.findall(r'\{\w+\}', obj)
            assert len(placeholders) == 0, \
                f"Found unsubstituted placeholders: {placeholders}"
        elif isinstance(obj, dict):
            for value in obj.values():
                self._check_no_placeholders(value)
        elif isinstance(obj, list):
            for item in obj:
                self._check_no_placeholders(item)


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_thesis_review_pattern(self):
        """
        Test pattern similar to real thesis review configs.
        
        Expected behavior: Complex nested patterns with multiple
        parameters should expand correctly.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'chapter_review': {
                    'pattern': [
                        {
                            'type': 'Markdown',
                            'liquid': '### {chapter_name}',
                            'args': {'layout': {'width': '800px'}}
                        },
                        {
                            'type': 'Checkbox',
                            'field': '{prefix}SummaryIncludeHistory',
                            'args': {
                                'description': 'Include custom query conversation as context',
                                'default': False
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}Summary',
                            'args': {
                                'description': 'Summary',
                                'placeholder': 'LLM-generated summary of {chapter_name} will appear here...',
                                'rows': 10
                            }
                        },
                        {
                            'type': 'PopulateButton',
                            'args': {
                                'target': '{prefix}Summary',
                                'compute': {
                                    'field': '{prefix}Summary',
                                    'function': 'llm_pdf_review',
                                    'view_args': {
                                        'filename': {
                                            'display': '{{{{Name}}}}_thesis_{filename}.pdf'
                                        }
                                    },
                                    'row_args': {
                                        'include_history': '{prefix}SummaryIncludeHistory',
                                        'model': 'summary_model'
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'chapter_review',
                    'instances': [
                        {'prefix': 'ch1', 'chapter_name': 'Chapter 1: Introduction', 'filename': 'ch1'},
                        {'prefix': 'ch2', 'chapter_name': 'Chapter 2: Background', 'filename': 'ch2'},
                        {'prefix': 'ch3', 'chapter_name': 'Chapter 3: Methods', 'filename': 'ch3'}
                    ]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'id',
                'data': {'id': ['test'], 'Name': ['TestStudent']}
            }
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            review = interface._config['review']
            
            # Should have 12 entries (3 chapters × 4 widgets each)
            assert len(review) == 12
            
            # Check first chapter's widgets
            assert review[0]['type'] == 'Markdown'
            assert review[0]['liquid'] == '### Chapter 1: Introduction'
            
            assert review[1]['type'] == 'Checkbox'
            assert review[1]['field'] == 'ch1SummaryIncludeHistory'
            
            assert review[2]['type'] == 'Textarea'
            assert review[2]['field'] == 'ch1Summary'
            assert 'Chapter 1: Introduction' in review[2]['args']['placeholder']
            
            assert review[3]['type'] == 'PopulateButton'
            assert review[3]['args']['target'] == 'ch1Summary'
            assert review[3]['args']['compute']['field'] == 'ch1Summary'
            assert review[3]['args']['compute']['row_args']['include_history'] == 'ch1SummaryIncludeHistory'
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_multiple_template_instances_order_preserved(self):
        """
        Test that instance order is preserved during expansion.
        
        Expected behavior: Template instances should expand in the
        order they are specified.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'ordered_template': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Field', 'order_marker': '{prefix}'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'ordered_template',
                    'instances': [
                        {'prefix': 'first'},
                        {'prefix': 'second'},
                        {'prefix': 'third'},
                        {'prefix': 'fourth'}
                    ]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'id',
                'data': {'id': ['test'], 'name': ['Test']}
            }
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            review = interface._config['review']
            
            # Check order is preserved
            assert len(review) == 4
            assert review[0]['field'] == 'firstField'
            assert review[0]['order_marker'] == 'first'
            assert review[1]['field'] == 'secondField'
            assert review[1]['order_marker'] == 'second'
            assert review[2]['field'] == 'thirdField'
            assert review[2]['order_marker'] == 'third'
            assert review[3]['field'] == 'fourthField'
            assert review[3]['order_marker'] == 'fourth'
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

