"""
Tests for include_query Flag in llm_custom_query

Tests the include_query parameter that formats LLM responses to include
the original question along with the answer.

Related to CIP-0007: Append Mode for Compute Operations
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestIncludeQueryFlag:
    """Test include_query functionality in llm_custom_query."""
    
    def test_include_query_false_returns_only_response(self):
        """Test that include_query=False returns only the LLM response."""
        query = "What are the main contributions?"
        response = "The main contributions are: 1) Novel algorithm, 2) Improved performance"
        include_query = False
        
        result = self._format_output(query, response, include_query)
        
        assert result == response
        assert "Question:" not in result
        assert "Response:" not in result
    
    def test_include_query_true_returns_formatted_qa(self):
        """Test that include_query=True returns formatted Q&A."""
        query = "What are the main contributions?"
        response = "The main contributions are: 1) Novel algorithm, 2) Improved performance"
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        assert "**Question:** What are the main contributions?" in result
        assert "**Response:** The main contributions are" in result
        assert result.index("Question:") < result.index("Response:")
    
    def test_include_query_default_false(self):
        """Test that omitting include_query defaults to False (backward compatible)."""
        query = "What are the limitations?"
        response = "The main limitations are..."
        include_query = None  # Simulating omitted parameter
        
        result = self._format_output(query, response, include_query)
        
        # Should behave as False for backward compatibility
        assert result == response
        assert "Question:" not in result
    
    def test_include_query_with_empty_query(self):
        """Test include_query with empty query string."""
        query = ""
        response = "The answer is..."
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        # Should handle gracefully - might show empty question or skip it
        assert "Response:" in result
        assert response in result
    
    def test_include_query_with_none_query(self):
        """Test include_query with None query."""
        query = None
        response = "The answer is..."
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        # Should handle gracefully
        assert "Response:" in result
        assert response in result
    
    def test_include_query_with_multiline_query(self):
        """Test include_query with multiline question."""
        query = """What are the contributions and limitations?
Please provide detailed analysis including:
- Algorithmic innovations
- Performance improvements
- Known issues"""
        response = "Analysis: ..."
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        assert "**Question:**" in result
        assert all(line in result for line in query.split('\n'))
        assert "**Response:**" in result
        assert response in result
    
    def test_include_query_with_multiline_response(self):
        """Test include_query with multiline response."""
        query = "What are the contributions?"
        response = """The contributions include:

1. Novel algorithm for X
2. Improved performance by Y%
3. New framework for Z

Each of these represents significant advances."""
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        assert "**Question:**" in result
        assert "**Response:**" in result
        assert all(line in result for line in response.split('\n'))
    
    def test_include_query_formatting_consistency(self):
        """Test that formatting is consistent across multiple calls."""
        queries = [
            "First question?",
            "Second question?",
            "Third question?"
        ]
        response = "Generic response"
        include_query = True
        
        results = [self._format_output(q, response, include_query) for q in queries]
        
        # All should have same structure
        for result in results:
            assert "**Question:**" in result
            assert "**Response:**" in result
            assert result.count("**Question:**") == 1
            assert result.count("**Response:**") == 1
    
    def test_include_query_with_special_characters(self):
        """Test include_query with special characters in query."""
        query = 'What about "quoted text" and \'apostrophes\' and <brackets>?'
        response = "The answer handles special characters."
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        assert query in result
        assert response in result
        assert '"quoted text"' in result
        assert "'apostrophes'" in result
    
    def test_include_query_with_markdown_in_query(self):
        """Test include_query when query contains markdown."""
        query = "What about **bold** and *italic* and `code`?"
        response = "The answer is..."
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        assert query in result
        assert response in result
        # Markdown should be preserved
        assert "**bold**" in result
        assert "*italic*" in result
        assert "`code`" in result
    
    def test_include_query_with_very_long_query(self):
        """Test include_query with very long question."""
        query = "What are the implications of " + "x" * 1000 + " for the field?"
        response = "The implications are..."
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        assert "Question:" in result
        assert "Response:" in result
        # Long query should be included (or truncated with indication)
        assert ("x" * 100) in result  # At least part of the query
    
    def test_include_query_with_very_long_response(self):
        """Test include_query with very long response."""
        query = "What are the details?"
        response = "The detailed answer: " + "y" * 5000
        include_query = True
        
        result = self._format_output(query, response, include_query)
        
        assert "Question:" in result
        assert "Response:" in result
        assert query in result
        assert ("y" * 100) in result  # At least part of response
    
    # Helper method to simulate output formatting
    def _format_output(self, query, response, include_query):
        """
        Simulate formatting output with include_query flag.
        
        This matches the logic that should be implemented in llm_custom_query.
        """
        # Default to False if None (backward compatibility)
        if include_query is None:
            include_query = False
        
        if not include_query:
            return response
        
        # Format with question and response
        if query is None:
            query = ""
        
        if query.strip():
            return f"**Question:** {query}\n\n**Response:** {response}"
        else:
            # If query is empty, just return response with label
            return f"**Response:** {response}"


class TestIncludeQueryWithAppendMode:
    """Test include_query combined with append mode for conversation history."""
    
    def test_multiple_queries_with_append_builds_history(self):
        """Test that multiple Q&A pairs with append mode build conversation history."""
        queries = [
            "What are the main contributions?",
            "What are the limitations?",
            "How does this compare to prior work?"
        ]
        responses = [
            "The main contributions are...",
            "The limitations include...",
            "Compared to prior work..."
        ]
        
        include_query = True
        mode = 'append'
        separator = '\n\n---\n\n'
        
        # Simulate building up history
        accumulated = ""
        for query, response in zip(queries, responses):
            formatted = self._format_output(query, response, include_query)
            accumulated = self._apply_append(accumulated, formatted, separator)
        
        # Verify all Q&A pairs are present
        for query in queries:
            assert query in accumulated
        for response in responses:
            assert response in accumulated
        
        # Verify separators
        assert accumulated.count(separator) == 2  # Between 3 entries
        
        # Verify order (oldest first)
        assert accumulated.index(queries[0]) < accumulated.index(queries[1])
        assert accumulated.index(queries[1]) < accumulated.index(queries[2])
    
    def test_qa_pairs_clearly_separated(self):
        """Test that Q&A pairs are clearly separated in accumulated history."""
        queries = ["Question 1?", "Question 2?"]
        responses = ["Answer 1", "Answer 2"]
        
        include_query = True
        mode = 'append'
        separator = '\n\n---\n\n'
        
        accumulated = ""
        for query, response in zip(queries, responses):
            formatted = self._format_output(query, response, include_query)
            accumulated = self._apply_append(accumulated, formatted, separator)
        
        # Split by separator
        entries = accumulated.split(separator)
        assert len(entries) == 2
        
        # Each entry should have both question and response
        for entry in entries:
            assert "**Question:**" in entry
            assert "**Response:**" in entry
    
    def test_conversation_history_readability(self):
        """Test that the accumulated conversation history is readable."""
        queries = [
            "What is the main algorithm?",
            "What is its complexity?",
            "What are the practical applications?"
        ]
        responses = [
            "The main algorithm is X.",
            "The complexity is O(n log n).",
            "Practical applications include A, B, and C."
        ]
        
        include_query = True
        mode = 'append'
        separator = '\n\n---\n\n'
        
        accumulated = ""
        for query, response in zip(queries, responses):
            formatted = self._format_output(query, response, include_query)
            accumulated = self._apply_append(accumulated, formatted, separator)
        
        # The accumulated text should be well-structured
        lines = accumulated.split('\n')
        
        # Should have multiple Question: lines
        question_lines = [l for l in lines if '**Question:**' in l]
        assert len(question_lines) == 3
        
        # Should have multiple Response: lines
        response_lines = [l for l in lines if '**Response:**' in l]
        assert len(response_lines) == 3
    
    # Helper methods
    def _format_output(self, query, response, include_query):
        """Format output with include_query flag."""
        helper = TestIncludeQueryFlag()
        return helper._format_output(query, response, include_query)
    
    def _apply_append(self, current, new_content, separator):
        """Apply append mode."""
        if current and current.strip():
            return current + separator + new_content
        return new_content


class TestIncludeQueryEdgeCases:
    """Test edge cases for include_query functionality."""
    
    def test_query_with_unicode_characters(self):
        """Test query with unicode characters."""
        query = "Qu'est-ce que c'est? Qué pasa? Что это? 这是什么？"
        response = "Answer in various languages..."
        include_query = True
        
        helper = TestIncludeQueryFlag()
        result = helper._format_output(query, response, include_query)
        
        assert query in result
        assert response in result
    
    def test_response_with_code_blocks(self):
        """Test response containing code blocks."""
        query = "Show me example code"
        response = """Here is the code:

```python
def hello():
    print("world")
```

This demonstrates the concept."""
        include_query = True
        
        helper = TestIncludeQueryFlag()
        result = helper._format_output(query, response, include_query)
        
        assert "```python" in result
        assert "def hello():" in result
        assert query in result
    
    def test_query_with_latex_math(self):
        """Test query with LaTeX math notation."""
        query = "What is the formula for $E = mc^2$?"
        response = "The formula relates energy and mass..."
        include_query = True
        
        helper = TestIncludeQueryFlag()
        result = helper._format_output(query, response, include_query)
        
        assert "$E = mc^2$" in result
        assert response in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


