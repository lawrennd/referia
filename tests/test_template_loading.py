"""
Test coverage for template loading functionality.

These tests follow Test-Driven Development (TDD) approach:
1. Write failing test (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor while keeping tests green

This module tests the template loading phase of template expansion,
ensuring templates can be loaded from inline definitions and external files.

Created as part of backlog item: 2025-12-22_implement-template-expansion.md
Related CIP: 0006 (Configuration Template Expansion System)
"""

import pytest
import tempfile
import os
import yaml
from referia.config.interface import Interface


class TestInlineTemplateLoading:
    """Test loading templates defined inline in configuration."""
    
    def test_load_single_inline_template(self):
        """
        Test loading a single template defined inline in configuration.
        
        Expected behavior: A template defined in the 'templates:' section
        should be loaded and available for expansion.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'test_template': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Comment'}
                    ]
                }
            },
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
            
            # Template should be loaded and stored
            assert hasattr(interface, '_templates'), \
                "Interface should have _templates attribute after loading config with templates"
            assert 'test_template' in interface._templates, \
                "test_template should be in loaded templates"
            assert 'pattern' in interface._templates['test_template'], \
                "Template should have pattern key"
            
        finally:
            # Cleanup
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_load_multiple_inline_templates(self):
        """
        Test loading multiple templates from same configuration.
        
        Expected behavior: Multiple templates can be defined and all
        should be available.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'chapter_review': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Summary'}
                    ]
                },
                'section_review': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Notes'}
                    ]
                }
            },
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
            
            # Both templates should be loaded
            assert hasattr(interface, '_templates')
            assert 'chapter_review' in interface._templates
            assert 'section_review' in interface._templates
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_load_template_with_complex_pattern(self):
        """
        Test loading template with nested structure.
        
        Expected behavior: Complex nested patterns should be preserved.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'complex_template': {
                    'pattern': [
                        {
                            'type': 'Checkbox',
                            'field': '{prefix}IncludeHistory',
                            'args': {
                                'description': 'Include history',
                                'default': False,
                                'layout': {'width': '400px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}Summary',
                            'args': {
                                'rows': 10,
                                'placeholder': 'Summary for {prefix}'
                            }
                        }
                    ]
                }
            },
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
            
            # Complex structure should be preserved
            assert 'complex_template' in interface._templates
            pattern = interface._templates['complex_template']['pattern']
            assert len(pattern) == 2
            assert pattern[0]['type'] == 'Checkbox'
            assert 'args' in pattern[0]
            assert 'layout' in pattern[0]['args']
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


class TestExternalTemplateLoading:
    """Test loading templates from external files."""
    
    def test_load_template_from_external_file(self):
        """
        Test loading a template from an external YAML file.
        
        Expected behavior: Template defined in external file should be
        loaded and available for use.
        
        TDD Status: RED - This test should fail initially
        """
        tmpdir = tempfile.mkdtemp()
        try:
            # Create external template file
            template_file = f"{tmpdir}/chapter_template.yml"
            template_content = {
                'pattern': [
                    {'type': 'Textarea', 'field': '{prefix}Summary'},
                    {'type': 'Textarea', 'field': '{prefix}Questions'}
                ]
            }
            with open(template_file, 'w') as f:
                yaml.dump(template_content, f)
            
            # Create config referencing external template
            config = {
                'templates': {
                    'chapter_review': {
                        'file': './chapter_template.yml'
                    }
                },
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
            
            # Template from external file should be loaded
            assert 'chapter_review' in interface._templates
            assert 'pattern' in interface._templates['chapter_review']
            assert len(interface._templates['chapter_review']['pattern']) == 2
            
        finally:
            if os.path.exists(template_file):
                os.remove(template_file)
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_external_template_file_not_found(self):
        """
        Test error handling when external template file doesn't exist.
        
        Expected behavior: Should raise ValueError with clear message
        indicating which file was not found.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'missing_template': {
                    'file': './nonexistent.yml'
                }
            },
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
            
            # Error message should be clear about which file is missing
            assert 'nonexistent.yml' in str(exc_info.value).lower()
            assert 'not found' in str(exc_info.value).lower() or \
                   'does not exist' in str(exc_info.value).lower()
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_external_template_malformed_yaml(self):
        """
        Test error handling when external template file has malformed YAML.
        
        Expected behavior: Should raise clear error about YAML parsing issue.
        
        TDD Status: RED - This test should fail initially
        """
        tmpdir = tempfile.mkdtemp()
        try:
            # Create malformed YAML file (invalid indentation)
            template_file = f"{tmpdir}/bad_template.yml"
            with open(template_file, 'w') as f:
                f.write("pattern:\n- type: Textarea\n field: bad_indent\n- another: entry")
            
            config = {
                'templates': {
                    'bad_template': {
                        'file': './bad_template.yml'
                    }
                },
                'input': {
                    'type': 'local',
                    'index': 'id',
                    'data': {'id': ['test'], 'name': ['Test']}
                }
            }
            
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            with pytest.raises((ValueError, yaml.YAMLError)) as exc_info:
                Interface.from_file(
                    user_file="_referia.yml",
                    directory=tmpdir
                )
            
            # Error should mention the template file
            error_message = str(exc_info.value).lower()
            assert 'bad_template' in error_message or 'yaml' in error_message
            
        finally:
            if os.path.exists(template_file):
                os.remove(template_file)
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


class TestTemplateValidation:
    """Test validation of template structure."""
    
    def test_template_missing_pattern_key(self):
        """
        Test error when template doesn't have 'pattern' key.
        
        Expected behavior: Should raise ValueError indicating pattern is required.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'invalid_template': {
                    'notpattern': [{'type': 'Textarea'}]
                }
            },
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
            
            assert 'pattern' in str(exc_info.value).lower()
            assert 'invalid_template' in str(exc_info.value)
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_template_pattern_not_list(self):
        """
        Test error when pattern is not a list.
        
        Expected behavior: Should raise ValueError indicating pattern must be a list.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'invalid_template': {
                    'pattern': 'not a list'
                }
            },
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
            
            error_message = str(exc_info.value).lower()
            assert 'pattern' in error_message
            assert 'list' in error_message or 'array' in error_message
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

