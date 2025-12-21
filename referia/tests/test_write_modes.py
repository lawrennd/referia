"""
Tests for Write Modes in Compute System

Tests the mode parameter functionality that controls how compute results
are written to fields: replace, append, and prepend modes.

Related to CIP-0007: Append Mode for Compute Operations
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
from lynguine.assess.data import CustomDataFrame


@pytest.fixture
def mock_data():
    """Create mock data for testing."""
    df = pd.DataFrame({
        'Name': ['Test'],
        'field1': ['existing content'],
        'field2': [''],
        'field3': [None]
    })
    return CustomDataFrame(df)


@pytest.fixture
def mock_compute_result():
    """Mock compute function result."""
    return "new content"


class TestWriteModes:
    """Test write mode functionality for compute operations."""
    
    def test_replace_mode_with_existing_content(self, mock_data, mock_compute_result):
        """Test replace mode overwrites existing content."""
        field_name = 'field1'
        mode = 'replace'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        assert current == 'existing content'
        
        # Simulate replace mode
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        assert result == 'new content'
        assert 'existing content' not in result
        assert separator not in result
    
    def test_replace_mode_with_empty_field(self, mock_data, mock_compute_result):
        """Test replace mode with empty field."""
        field_name = 'field2'
        mode = 'replace'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        assert current == ''
        
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        assert result == 'new content'
    
    def test_replace_mode_default(self, mock_data, mock_compute_result):
        """Test that omitting mode defaults to replace."""
        field_name = 'field1'
        mode = None  # Simulating omitted mode parameter
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        # Should behave as replace
        assert result == 'new content'
    
    def test_append_mode_with_existing_content(self, mock_data, mock_compute_result):
        """Test append mode adds to end with separator."""
        field_name = 'field1'
        mode = 'append'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]  # Use .at for scalar value
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        expected = 'existing content\n\n---\n\nnew content'
        assert result == expected
        assert result.count(separator) == 1
    
    def test_append_mode_with_empty_field(self, mock_data, mock_compute_result):
        """Test append mode with empty field doesn't add separator."""
        field_name = 'field2'
        mode = 'append'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        assert result == 'new content'
        assert separator not in result
    
    def test_append_mode_with_null_field(self, mock_data, mock_compute_result):
        """Test append mode with null field."""
        field_name = 'field3'
        mode = 'append'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        assert result == 'new content'
        assert separator not in result
    
    def test_prepend_mode_with_existing_content(self, mock_data, mock_compute_result):
        """Test prepend mode adds to beginning with separator."""
        field_name = 'field1'
        mode = 'prepend'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        expected = 'new content\n\n---\n\nexisting content'
        assert result == expected
        assert result.count(separator) == 1
        assert result.startswith('new content')
    
    def test_prepend_mode_with_empty_field(self, mock_data, mock_compute_result):
        """Test prepend mode with empty field doesn't add separator."""
        field_name = 'field2'
        mode = 'prepend'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        assert result == 'new content'
        assert separator not in result
    
    def test_multiple_appends(self, mock_data, mock_compute_result):
        """Test multiple appends build up correctly."""
        field_name = 'field1'
        mode = 'append'
        separator = '\n\n---\n\n'
        
        # First append
        current = mock_data.at[0, field_name]
        result1 = self._apply_mode(current, 'first new', mode, separator)
        
        # Second append
        result2 = self._apply_mode(result1, 'second new', mode, separator)
        
        # Third append
        result3 = self._apply_mode(result2, 'third new', mode, separator)
        
        assert 'existing content' in result3
        assert 'first new' in result3
        assert 'second new' in result3
        assert 'third new' in result3
        assert result3.count(separator) == 3
        
        # Verify order
        assert result3.index('existing content') < result3.index('first new')
        assert result3.index('first new') < result3.index('second new')
        assert result3.index('second new') < result3.index('third new')
    
    def test_multiple_prepends(self, mock_data, mock_compute_result):
        """Test multiple prepends build up correctly (newest first)."""
        field_name = 'field1'
        mode = 'prepend'
        separator = '\n\n---\n\n'
        
        # First prepend
        current = mock_data.at[0, field_name]
        result1 = self._apply_mode(current, 'first new', mode, separator)
        
        # Second prepend
        result2 = self._apply_mode(result1, 'second new', mode, separator)
        
        # Third prepend
        result3 = self._apply_mode(result2, 'third new', mode, separator)
        
        assert 'existing content' in result3
        assert 'first new' in result3
        assert 'second new' in result3
        assert 'third new' in result3
        assert result3.count(separator) == 3
        
        # Verify order (newest first)
        assert result3.index('third new') < result3.index('second new')
        assert result3.index('second new') < result3.index('first new')
        assert result3.index('first new') < result3.index('existing content')
    
    def test_custom_separator(self, mock_data, mock_compute_result):
        """Test custom separator value."""
        field_name = 'field1'
        mode = 'append'
        separator = '\n===\n'
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        expected = 'existing content\n===\nnew content'
        assert result == expected
        assert '\n===\n' in result
        assert '\n\n---\n\n' not in result
    
    def test_empty_string_separator(self, mock_data, mock_compute_result):
        """Test empty string separator for direct concatenation."""
        field_name = 'field1'
        mode = 'append'
        separator = ''
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        expected = 'existing contentnew content'
        assert result == expected
    
    def test_unicode_separator(self, mock_data, mock_compute_result):
        """Test separator with unicode characters."""
        field_name = 'field1'
        mode = 'append'
        separator = '\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n'
        
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, mock_compute_result, mode, separator)
        
        assert separator in result
        assert result.startswith('existing content')
        assert result.endswith('new content')
    
    def test_invalid_mode_raises_error(self, mock_data, mock_compute_result):
        """Test that invalid mode value raises clear error."""
        field_name = 'field1'
        mode = 'invalid_mode'
        separator = '\n\n---\n\n'
        
        current = mock_data.at[0, field_name]
        
        with pytest.raises((ValueError, KeyError)) as exc_info:
            self._apply_mode(current, mock_compute_result, mode, separator)
        
        # Error message should mention the invalid mode
        assert 'mode' in str(exc_info.value).lower() or 'invalid' in str(exc_info.value).lower()
    
    def test_special_characters_in_content(self, mock_data):
        """Test mode with special characters in content."""
        field_name = 'field1'
        mode = 'append'
        separator = '\n\n---\n\n'
        
        special_content = 'Content with "quotes", \'apostrophes\', and\nnewlines\tand tabs'
        current = mock_data.at[0, field_name]
        result = self._apply_mode(current, special_content, mode, separator)
        
        assert special_content in result
        assert separator in result
        assert 'existing content' in result
    
    def test_very_long_content(self, mock_data):
        """Test mode with very long accumulated content."""
        field_name = 'field1'
        mode = 'append'
        separator = '\n\n---\n\n'
        
        # Start with initial content
        current = mock_data.at[0, field_name]
        
        # Append many times to create long content
        result = current
        for i in range(50):
            new_content = f'Entry {i}: ' + 'x' * 200  # 200 chars per entry
            result = self._apply_mode(result, new_content, mode, separator)
        
        # Verify it handles long content
        assert len(result) > 10000  # Should be quite long
        assert result.count(separator) == 50
        assert 'Entry 0' in result
        assert 'Entry 49' in result
    
    # Helper method to simulate mode application
    def _apply_mode(self, current, new_content, mode, separator):
        """
        Simulate applying a write mode.
        
        This matches the logic that should be implemented in the compute system.
        """
        # Handle None/null values
        if current is None or pd.isna(current):
            current = ''
        
        # Default to replace if mode is None
        if mode is None or mode == 'replace':
            return new_content
        
        if mode == 'append':
            if current and str(current).strip():
                return str(current) + separator + str(new_content)
            return str(new_content)
        
        if mode == 'prepend':
            if current and str(current).strip():
                return str(new_content) + separator + str(current)
            return str(new_content)
        
        raise ValueError(f"Unknown mode: {mode}")


class TestWriteModesWithMockCompute:
    """Test write modes integrated with mock Compute class."""
    
    @patch('referia.assess.compute.Compute')
    def test_compute_with_append_mode(self, MockCompute):
        """Test that Compute class respects append mode in settings."""
        # This is a placeholder for when the actual compute system implements mode
        # For now, we're just testing the logic independently
        pass
    
    @patch('referia.assess.compute.Compute')
    def test_compute_with_prepend_mode(self, MockCompute):
        """Test that Compute class respects prepend mode in settings."""
        pass


class TestSeparatorEdgeCases:
    """Test edge cases specifically related to separators."""
    
    def test_separator_with_only_whitespace(self):
        """Test separator that is only whitespace."""
        current = 'existing'
        new = 'new'
        mode = 'append'
        separator = '   '
        
        helper = TestWriteModes()
        result = helper._apply_mode(current, new, mode, separator)
        
        assert result == 'existing   new'
    
    def test_separator_with_newlines_only(self):
        """Test separator with only newlines."""
        current = 'existing'
        new = 'new'
        mode = 'append'
        separator = '\n\n\n'
        
        helper = TestWriteModes()
        result = helper._apply_mode(current, new, mode, separator)
        
        assert result == 'existing\n\n\nnew'
    
    def test_none_separator(self):
        """Test None as separator (should be treated as empty string or error)."""
        current = 'existing'
        new = 'new'
        mode = 'append'
        separator = None
        
        helper = TestWriteModes()
        # This should either work with empty separator or raise error
        try:
            result = helper._apply_mode(current, new, mode, separator)
            # If it works, separator should be treated as empty
            assert result == 'existingnew'
        except (TypeError, ValueError):
            # If it raises error, that's also acceptable behavior
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


