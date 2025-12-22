"""
Test coverage for parameter substitution in templates.

These tests follow Test-Driven Development (TDD) approach:
1. Write failing test (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor while keeping tests green

This module tests parameter substitution, ensuring template parameters
like {prefix}, {filename}, etc. are correctly replaced with instance values.

Created as part of backlog item: 2025-12-22_implement-template-expansion.md
Related CIP: 0006 (Configuration Template Expansion System)
"""

import pytest
import tempfile
import os
import yaml
from referia.config.interface import Interface


class TestSimpleSubstitution:
    """Test basic parameter substitution in templates."""
    
    def test_simple_field_substitution(self):
        """
        Test simple {prefix} substitution in field name.
        
        Expected behavior: {prefix} should be replaced with instance value.
        
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
                {
                    'template': 'simple_template',
                    'instances': [
                        {'prefix': 'ch1'},
                        {'prefix': 'ch2'}
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
            
            # Should have expanded review with substituted parameters
            assert 'review' in interface._config
            review = interface._config['review']
            
            # Should have 2 expanded entries (one per instance)
            assert len(review) >= 2
            
            # Check first instance has ch1Comment
            found_ch1 = False
            found_ch2 = False
            for entry in review:
                if 'field' in entry and entry['field'] == 'ch1Comment':
                    found_ch1 = True
                if 'field' in entry and entry['field'] == 'ch2Comment':
                    found_ch2 = True
            
            assert found_ch1, "Should find ch1Comment in expanded review"
            assert found_ch2, "Should find ch2Comment in expanded review"
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_multiple_substitutions_in_one_string(self):
        """
        Test multiple parameter substitutions in one string.
        
        Expected behavior: {prefix}_{suffix} with prefix=ch1, suffix=Summary
        should become ch1_Summary.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'multi_param': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}_{suffix}'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'multi_param',
                    'instances': [
                        {'prefix': 'ch1', 'suffix': 'Summary'}
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
            
            # Check substitution result
            review = interface._config['review']
            found = any(
                entry.get('field') == 'ch1_Summary' 
                for entry in review
            )
            assert found, "Should find ch1_Summary in expanded review"
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_substitution_in_nested_dict(self):
        """
        Test parameter substitution in nested dictionary structures.
        
        Expected behavior: Parameters in nested args should be substituted.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'nested_template': {
                    'pattern': [
                        {
                            'type': 'Textarea',
                            'field': '{prefix}Comment',
                            'args': {
                                'description': 'Comments for {prefix}',
                                'placeholder': 'Enter {prefix} comments here',
                                'layout': {'width': '800px'}
                            }
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'nested_template',
                    'instances': [{'prefix': 'ch1'}]
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
            
            # Find the expanded entry
            review = interface._config['review']
            entry = None
            for e in review:
                if e.get('field') == 'ch1Comment':
                    entry = e
                    break
            
            assert entry is not None, "Should find expanded entry"
            assert 'args' in entry
            assert entry['args']['description'] == 'Comments for ch1'
            assert entry['args']['placeholder'] == 'Enter ch1 comments here'
            assert entry['args']['layout']['width'] == '800px'  # Not substituted
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


class TestErrorHandling:
    """Test error handling for parameter substitution."""
    
    def test_missing_required_parameter(self):
        """
        Test error when required parameter is missing.
        
        Expected behavior: Should raise ValueError with clear message
        about which parameter is missing.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'needs_prefix': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Comment'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'needs_prefix',
                    'instances': [
                        {'notprefix': 'ch1'}  # Wrong parameter name
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
            
            with pytest.raises(ValueError) as exc_info:
                Interface.from_file(
                    user_file="_referia.yml",
                    directory=tmpdir
                )
            
            # Error should mention the missing parameter
            error_message = str(exc_info.value).lower()
            assert 'prefix' in error_message
            assert 'missing' in error_message or 'required' in error_message
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_extra_parameters_ignored(self):
        """
        Test that extra parameters (not used in template) are ignored.
        
        Expected behavior: Extra parameters should not cause errors.
        
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
                {
                    'template': 'simple_template',
                    'instances': [
                        {
                            'prefix': 'ch1',
                            'extra_param': 'ignored',
                            'another_extra': 'also_ignored'
                        }
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
            
            # Should not raise error
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            # Check substitution worked
            review = interface._config['review']
            found = any(
                entry.get('field') == 'ch1Comment' 
                for entry in review
            )
            assert found, "Should find ch1Comment despite extra parameters"
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


class TestEdgeCases:
    """Test edge cases in parameter substitution."""
    
    def test_empty_parameter_value(self):
        """
        Test substitution with empty string parameter value.
        
        Expected behavior: Empty string should be substituted, resulting
        in field name like 'Comment' (no prefix).
        
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
                {
                    'template': 'simple_template',
                    'instances': [{'prefix': ''}]
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
            
            # Check substitution result
            review = interface._config['review']
            found = any(
                entry.get('field') == 'Comment' 
                for entry in review
            )
            assert found, "Should find 'Comment' (empty prefix)"
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_numeric_parameter_value(self):
        """
        Test substitution with numeric parameter value.
        
        Expected behavior: Numeric values should be converted to string.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'chapter_template': {
                    'pattern': [
                        {'type': 'Textarea', 'field': 'chapter{num}Comment'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'chapter_template',
                    'instances': [
                        {'num': 1},
                        {'num': 2}
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
            
            # Check substitution results
            review = interface._config['review']
            found_1 = any(entry.get('field') == 'chapter1Comment' for entry in review)
            found_2 = any(entry.get('field') == 'chapter2Comment' for entry in review)
            
            assert found_1, "Should find chapter1Comment"
            assert found_2, "Should find chapter2Comment"
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_special_characters_in_value(self):
        """
        Test substitution with special characters in parameter value.
        
        Expected behavior: Special characters should be preserved.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'file_template': {
                    'pattern': [
                        {
                            'type': 'Textarea',
                            'args': {
                                'filename': '{filepath}'
                            }
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'file_template',
                    'instances': [
                        {'filepath': '/path/to/file-name_v2.pdf'}
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
            
            # Check substitution preserved special characters
            review = interface._config['review']
            found = any(
                entry.get('args', {}).get('filename') == '/path/to/file-name_v2.pdf'
                for entry in review
            )
            assert found, "Should preserve special characters in substitution"
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_no_substitution_when_no_placeholders(self):
        """
        Test that strings without {placeholders} are left unchanged.
        
        Expected behavior: Static values should remain exactly as-is.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'static_template': {
                    'pattern': [
                        {
                            'type': 'Textarea',
                            'field': 'StaticFieldName',
                            'args': {
                                'description': 'No placeholders here',
                                'rows': 10
                            }
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'static_template',
                    'instances': [{'prefix': 'ch1'}]  # Parameter not used
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
            
            # Check static values unchanged
            review = interface._config['review']
            entry = next(
                (e for e in review if e.get('field') == 'StaticFieldName'),
                None
            )
            
            assert entry is not None
            assert entry['args']['description'] == 'No placeholders here'
            assert entry['args']['rows'] == 10
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


class TestComplexSubstitution:
    """Test complex substitution scenarios."""
    
    def test_nested_list_substitution(self):
        """
        Test parameter substitution in lists within pattern.
        
        Expected behavior: Parameters in list elements should be substituted.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'list_template': {
                    'pattern': [
                        {
                            'type': 'Group',
                            'entries': [
                                {'type': 'Textarea', 'field': '{prefix}Summary'},
                                {'type': 'Textarea', 'field': '{prefix}Questions'}
                            ]
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'list_template',
                    'instances': [{'prefix': 'ch1'}]
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
            
            # Check nested list substitution
            review = interface._config['review']
            
            # Find the group entry
            group_entry = None
            for entry in review:
                if entry.get('type') == 'Group' and 'entries' in entry:
                    group_entry = entry
                    break
            
            assert group_entry is not None, "Should find Group entry"
            entries = group_entry['entries']
            
            fields = [e.get('field') for e in entries if 'field' in e]
            assert 'ch1Summary' in fields
            assert 'ch1Questions' in fields
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

