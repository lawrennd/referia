"""
Test coverage for template expansion regression testing.

These tests follow Test-Driven Development (TDD) approach:
1. Write failing test (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor while keeping tests green

This module tests template expansion against real-world thesis review
configurations to ensure the feature works correctly in production scenarios.

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


class TestThesisReviewRegression:
    """Test template expansion against real thesis review patterns."""
    
    def test_simple_chapter_pattern_expansion(self):
        """
        Test expanding a simple chapter review pattern similar to thesis configs.
        
        This simulates the repetitive pattern seen in real thesis review configs
        where the same structure (Summary, Questions, etc.) is repeated for
        each chapter.
        
        TDD Status: RED - This test should fail initially
        """
        # Create a template that mimics the thesis review pattern
        config = {
            'templates': {
                'chapter_review': {
                    'pattern': [
                        {
                            'type': 'Markdown',
                            'liquid': '### {chapter_title}',
                            'args': {'layout': {'width': '800px'}}
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}Summary',
                            'args': {
                                'description': 'Summary',
                                'placeholder': 'Enter summary...',
                                'rows': 10,
                                'layout': {'width': '800px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}Questions',
                            'args': {
                                'description': 'Questions',
                                'placeholder': 'Enter questions...',
                                'rows': 5,
                                'layout': {'width': '800px'}
                            }
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'chapter_review',
                    'instances': [
                        {'prefix': 'ch1', 'chapter_title': 'Chapter 1'},
                        {'prefix': 'ch2', 'chapter_title': 'Chapter 2'},
                        {'prefix': 'ch3', 'chapter_title': 'Chapter 3'},
                        {'prefix': 'ch4', 'chapter_title': 'Chapter 4'},
                        {'prefix': 'ch5', 'chapter_title': 'Chapter 5'},
                        {'prefix': 'ch6', 'chapter_title': 'Chapter 6'},
                        {'prefix': 'ch7', 'chapter_title': 'Chapter 7'},
                        {'prefix': 'ch8', 'chapter_title': 'Chapter 8'},
                        {'prefix': 'ch9', 'chapter_title': 'Chapter 9'},
                        {'prefix': 'ch10', 'chapter_title': 'Chapter 10'},
                        {'prefix': 'ch11', 'chapter_title': 'Chapter 11'},
                        {'prefix': 'ch12', 'chapter_title': 'Chapter 12'},
                    ]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'Name',
                'data': {'Name': ['TestStudent']}
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
            
            # Should have 36 entries (12 chapters × 3 widgets each)
            assert len(review) == 36, \
                f"Expected 36 review entries (12 chapters × 3 widgets), got {len(review)}"
            
            # Verify first chapter's entries
            assert review[0]['type'] == 'Markdown'
            assert review[0]['liquid'] == '### Chapter 1'
            
            assert review[1]['field'] == 'ch1Summary'
            assert review[2]['field'] == 'ch1Questions'
            
            # Verify last chapter's entries
            assert review[33]['type'] == 'Markdown'
            assert review[33]['liquid'] == '### Chapter 12'
            
            assert review[34]['field'] == 'ch12Summary'
            assert review[35]['field'] == 'ch12Questions'
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_full_thesis_review_pattern(self):
        """
        Test the full thesis review pattern with all elements from real configs.
        
        This includes Summary, GeneralComments, DetailedComments, Questions,
        CustomPrompt/Response, PopulateButtons, Checkboxes, etc.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'full_chapter_review': {
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
                                'default': False,
                                'layout': {'width': '400px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}Summary',
                            'args': {
                                'description': 'Summary',
                                'placeholder': 'LLM-generated summary will appear here...',
                                'rows': 10,
                                'layout': {'width': '800px'}
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
                                            'display': '{{{{Name}}}}_thesis_{pdf_name}.pdf'
                                        }
                                    },
                                    'row_args': {
                                        'include_history': '{prefix}SummaryIncludeHistory',
                                        'model': 'summary_model',
                                        'temperature': 'summary_temp'
                                    }
                                },
                                'description': 'Generate Summary',
                                'layout': {'width': '200px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}GeneralComments',
                            'args': {
                                'description': 'General Comments',
                                'placeholder': 'Enter general comments...',
                                'rows': 10,
                                'layout': {'width': '800px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}DetailedComments',
                            'args': {
                                'description': 'Detailed Comments',
                                'placeholder': 'Enter detailed comments...',
                                'rows': 10,
                                'layout': {'width': '800px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}Questions',
                            'args': {
                                'description': 'Questions',
                                'placeholder': 'Enter questions...',
                                'rows': 5,
                                'layout': {'width': '800px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}CustomPrompt',
                            'args': {
                                'description': 'Custom Query',
                                'placeholder': 'Enter custom query...',
                                'rows': 3,
                                'layout': {'width': '800px'}
                            }
                        },
                        {
                            'type': 'Textarea',
                            'field': '{prefix}CustomResponse',
                            'args': {
                                'description': 'Custom Response',
                                'placeholder': 'LLM response will appear here...',
                                'rows': 10,
                                'layout': {'width': '800px'}
                            }
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'full_chapter_review',
                    'instances': [
                        {'prefix': 'ch1', 'chapter_name': 'Chapter 1', 'pdf_name': 'ch1'},
                        {'prefix': 'ch2', 'chapter_name': 'Chapter 2', 'pdf_name': 'ch2'},
                        {'prefix': 'ch3', 'chapter_name': 'Chapter 3', 'pdf_name': 'ch3'},
                    ]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'Name',
                'data': {'Name': ['Student'], 'summary_model': ['gpt-4'], 'summary_temp': [0.3]}
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
            
            # Should have 27 entries (3 chapters × 9 widgets each)
            assert len(review) == 27
            
            # Verify all field types are present for first chapter
            fields = [e.get('field') for e in review[:9]]
            expected_fields = [
                'ch1SummaryIncludeHistory',
                'ch1Summary',
                'ch1GeneralComments',
                'ch1DetailedComments',
                'ch1Questions',
                'ch1CustomPrompt',
                'ch1CustomResponse'
            ]
            for expected in expected_fields:
                assert expected in fields, f"Expected field {expected} not found"
            
            # Verify PopulateButton has correct substitution
            populate_button = review[3]
            assert populate_button['type'] == 'PopulateButton'
            assert populate_button['args']['target'] == 'ch1Summary'
            assert populate_button['args']['compute']['field'] == 'ch1Summary'
            # Liquid template should NOT be substituted
            assert '{{Name}}' in populate_button['args']['compute']['view_args']['filename']['display']
            assert '_ch1.pdf' in populate_button['args']['compute']['view_args']['filename']['display']
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_mixed_section_types(self):
        """
        Test templates for different section types (abstract, chapters, appendix, etc.).
        
        Real thesis configs have different patterns for different sections.
        
        TDD Status: RED - This test should fail initially
        """
        config = {
            'templates': {
                'full_chapter': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Summary'},
                        {'type': 'Textarea', 'field': '{prefix}GeneralComments'},
                        {'type': 'Textarea', 'field': '{prefix}DetailedComments'},
                        {'type': 'Textarea', 'field': '{prefix}Questions'}
                    ]
                },
                'simple_section': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}GeneralComments'},
                        {'type': 'Textarea', 'field': '{prefix}DetailedComments'}
                    ]
                }
            },
            'review': [
                # Abstract and TOC use simple pattern
                {
                    'template': 'simple_section',
                    'instances': [
                        {'prefix': 'abstract'},
                        {'prefix': 'toc'}
                    ]
                },
                # Chapters use full pattern
                {
                    'template': 'full_chapter',
                    'instances': [
                        {'prefix': 'ch1'},
                        {'prefix': 'ch2'},
                        {'prefix': 'ch3'}
                    ]
                },
                # References and appendix use simple pattern
                {
                    'template': 'simple_section',
                    'instances': [
                        {'prefix': 'ref'},
                        {'prefix': 'app'}
                    ]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'Name',
                'data': {'Name': ['Student']}
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
            
            # Should have: 2*2 (abstract, toc) + 3*4 (ch1-3) + 2*2 (ref, app) = 20
            assert len(review) == 20
            
            # Verify different sections have correct fields
            fields = [e.get('field') for e in review]
            
            # Simple sections
            assert 'abstractGeneralComments' in fields
            assert 'abstractDetailedComments' in fields
            assert 'abstractSummary' not in fields  # Should not have Summary
            
            # Full chapters
            assert 'ch1Summary' in fields
            assert 'ch1GeneralComments' in fields
            assert 'ch1DetailedComments' in fields
            assert 'ch1Questions' in fields
            
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            os.rmdir(tmpdir)
    
    def test_template_reduces_config_size(self):
        """
        Test that using templates significantly reduces configuration size.
        
        This is the main motivation for CIP-0006: reduce 2700+ line configs
        to ~50-100 lines.
        
        TDD Status: RED - This test should fail initially
        """
        # First create explicit config (like current thesis configs)
        explicit_chapters = []
        for i in range(1, 13):  # 12 chapters
            prefix = f'ch{i}'
            explicit_chapters.extend([
                {
                    'type': 'Markdown',
                    'liquid': f'### Chapter {i}'
                },
                {
                    'type': 'Textarea',
                    'field': f'{prefix}Summary',
                    'args': {'rows': 10}
                },
                {
                    'type': 'Textarea',
                    'field': f'{prefix}Questions',
                    'args': {'rows': 5}
                }
            ])
        
        explicit_config = {
            'review': explicit_chapters,
            'input': {
                'type': 'local',
                'index': 'Name',
                'data': {'Name': ['Student']}
            }
        }
        
        # Now create templated config
        templated_config = {
            'templates': {
                'chapter': {
                    'pattern': [
                        {'type': 'Markdown', 'liquid': '### Chapter {num}'},
                        {'type': 'Textarea', 'field': 'ch{num}Summary', 'args': {'rows': 10}},
                        {'type': 'Textarea', 'field': 'ch{num}Questions', 'args': {'rows': 5}}
                    ]
                }
            },
            'review': [
                {
                    'template': 'chapter',
                    'instances': [{'num': i} for i in range(1, 13)]
                }
            ],
            'input': {
                'type': 'local',
                'index': 'Name',
                'data': {'Name': ['Student']}
            }
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            # Test explicit config
            explicit_file = f"{tmpdir}/_referia_explicit.yml"
            with open(explicit_file, 'w') as f:
                yaml.dump(explicit_config, f)
            
            interface_explicit = Interface.from_file(
                user_file="_referia_explicit.yml",
                directory=tmpdir
            )
            
            # Test templated config
            templated_file = f"{tmpdir}/_referia_templated.yml"
            with open(templated_file, 'w') as f:
                yaml.dump(templated_config, f)
            
            interface_templated = Interface.from_file(
                user_file="_referia_templated.yml",
                directory=tmpdir
            )
            
            # Both should produce identical review structures
            review_explicit = interface_explicit._config['review']
            review_templated = interface_templated._config['review']
            
            assert len(review_explicit) == len(review_templated) == 36
            
            # Compare fields (order should be same)
            for i, (exp, tpl) in enumerate(zip(review_explicit, review_templated)):
                assert exp.get('type') == tpl.get('type'), \
                    f"Entry {i}: type mismatch"
                assert exp.get('field') == tpl.get('field'), \
                    f"Entry {i}: field mismatch"
            
            # Check file sizes
            explicit_size = os.path.getsize(explicit_file)
            templated_size = os.path.getsize(templated_file)
            
            # Templated should be significantly smaller
            reduction_ratio = explicit_size / templated_size
            assert reduction_ratio > 2.0, \
                f"Expected templated config to be >50% smaller, got {reduction_ratio:.1f}x reduction"
            
            print(f"\nConfig size reduction: {reduction_ratio:.1f}x")
            print(f"Explicit: {explicit_size} bytes")
            print(f"Templated: {templated_size} bytes")
            
        finally:
            if os.path.exists(explicit_file):
                os.remove(explicit_file)
            if os.path.exists(templated_file):
                os.remove(templated_file)
            os.rmdir(tmpdir)


class TestRealWorldScenarios:
    """Test scenarios based on actual thesis review workflow."""
    
    def test_drafts_vs_examined_pattern_difference(self):
        """
        Test different patterns for drafts vs examined theses.
        
        Drafts use LLM tools (PopulateButton), examined use manual entry.
        
        TDD Status: RED - This test should fail initially
        """
        # Draft pattern with LLM tools
        draft_config = {
            'templates': {
                'draft_chapter': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}Summary'},
                        {
                            'type': 'PopulateButton',
                            'args': {
                                'target': '{prefix}Summary',
                                'compute': {'field': '{prefix}Summary', 'function': 'llm_summarize'}
                            }
                        }
                    ]
                }
            },
            'review': [
                {
                    'template': 'draft_chapter',
                    'instances': [{'prefix': 'ch1'}, {'prefix': 'ch2'}]
                }
            ],
            'input': {'type': 'local', 'index': 'id', 'data': {'id': ['test']}}
        }
        
        # Examined pattern without LLM tools
        examined_config = {
            'templates': {
                'examined_chapter': {
                    'pattern': [
                        {'type': 'Textarea', 'field': '{prefix}GeneralComments'},
                        {'type': 'Textarea', 'field': '{prefix}DetailedComments'}
                    ]
                }
            },
            'review': [
                {
                    'template': 'examined_chapter',
                    'instances': [{'prefix': 'ch1'}, {'prefix': 'ch2'}]
                }
            ],
            'input': {'type': 'local', 'index': 'id', 'data': {'id': ['test']}}
        }
        
        tmpdir = tempfile.mkdtemp()
        try:
            # Test draft config
            draft_file = f"{tmpdir}/_referia_draft.yml"
            with open(draft_file, 'w') as f:
                yaml.dump(draft_config, f)
            
            interface_draft = Interface.from_file(
                user_file="_referia_draft.yml",
                directory=tmpdir
            )
            
            review_draft = interface_draft._config['review']
            assert len(review_draft) == 4  # 2 chapters × 2 widgets
            assert any(e.get('type') == 'PopulateButton' for e in review_draft)
            
            # Test examined config
            examined_file = f"{tmpdir}/_referia_examined.yml"
            with open(examined_file, 'w') as f:
                yaml.dump(examined_config, f)
            
            interface_examined = Interface.from_file(
                user_file="_referia_examined.yml",
                directory=tmpdir
            )
            
            review_examined = interface_examined._config['review']
            assert len(review_examined) == 4  # 2 chapters × 2 widgets
            assert not any(e.get('type') == 'PopulateButton' for e in review_examined)
            
        finally:
            if os.path.exists(draft_file):
                os.remove(draft_file)
            if os.path.exists(examined_file):
                os.remove(examined_file)
            os.rmdir(tmpdir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

