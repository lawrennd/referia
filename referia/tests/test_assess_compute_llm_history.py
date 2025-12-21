"""
Tests for LLM History Parameter Functionality

Tests the include_history and history parameters added to llm_custom_query 
and llm_pdf_review functions.
"""

import pytest
from unittest.mock import Mock, patch

# Test if LLM dependencies are available
try:
    from referia.util.llm import LLMManager, get_llm_manager, reset_llm_manager
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="LLM dependencies not installed")


@pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")
class TestLLMCustomQueryHistory:
    """Test llm_custom_query with history parameters."""
    
    def setup_method(self):
        """Reset LLM manager before each test."""
        reset_llm_manager()
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_history_disabled_by_default(self, mock_get_manager, mock_pdf_extract):
        """Test that history is not included when include_history=False (default)."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Response without history"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function without history parameters (default behavior)
        result = custom_query_func(
            custom_prompt='What are the contributions?',
            filename='chapter.pdf',
            start_page=1,
            directory='/test/dir'
        )
        
        # Verify result
        assert result == "Response without history"
        
        # Verify the prompt passed to LLM does NOT contain history
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert "## Previous Conversation" not in prompt_arg
        assert "## Chapter Content" in prompt_arg
        assert "## Current Question" in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_history_enabled_with_content(self, mock_get_manager, mock_pdf_extract):
        """Test that history is included when include_history=True and history has content."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Follow-up response referencing history"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Previous conversation history
        previous_history = (
            "**Question:** What are the main contributions?\n\n"
            "**Response:** The main contributions are X, Y, and Z."
        )
        
        # Call function with history enabled
        result = custom_query_func(
            custom_prompt='Can you explain contribution Y in more detail?',
            filename='chapter.pdf',
            start_page=1,
            directory='/test/dir',
            include_history=True,
            history=previous_history
        )
        
        # Verify result
        assert result == "Follow-up response referencing history"
        
        # Verify the prompt passed to LLM DOES contain history
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert "## Previous Conversation" in prompt_arg
        assert previous_history in prompt_arg
        assert "## Chapter Content" in prompt_arg
        assert "## Current Question" in prompt_arg
        assert "Can you explain contribution Y" in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_history_enabled_but_empty(self, mock_get_manager, mock_pdf_extract):
        """Test that empty history is not included even when include_history=True."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Response without history"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function with history enabled but empty string
        result = custom_query_func(
            custom_prompt='What are the contributions?',
            filename='chapter.pdf',
            start_page=1,
            directory='/test/dir',
            include_history=True,
            history=""
        )
        
        # Verify the prompt does NOT contain history section
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert "## Previous Conversation" not in prompt_arg
        assert "## Chapter Content" in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_history_enabled_but_none(self, mock_get_manager, mock_pdf_extract):
        """Test that None history is not included even when include_history=True."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Response without history"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function with history enabled but None value
        result = custom_query_func(
            custom_prompt='What are the contributions?',
            filename='chapter.pdf',
            start_page=1,
            directory='/test/dir',
            include_history=True,
            history=None
        )
        
        # Verify the prompt does NOT contain history section
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert "## Previous Conversation" not in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_history_with_multiple_exchanges(self, mock_get_manager, mock_pdf_extract):
        """Test history with multiple Q&A exchanges."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Response building on previous exchanges"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Multiple previous exchanges
        previous_history = (
            "**Question:** What are the main contributions?\n\n"
            "**Response:** The main contributions are X, Y, and Z.\n\n"
            "---\n\n"
            "**Question:** Tell me more about contribution X.\n\n"
            "**Response:** Contribution X is a novel approach to..."
        )
        
        # Call function with accumulated history
        result = custom_query_func(
            custom_prompt='How does contribution Y relate to contribution X?',
            filename='chapter.pdf',
            start_page=1,
            directory='/test/dir',
            include_history=True,
            history=previous_history
        )
        
        # Verify the full history is in the prompt
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert "## Previous Conversation" in prompt_arg
        assert "contribution X" in prompt_arg
        assert "contribution Y" in prompt_arg
        assert "novel approach" in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_history_with_special_characters(self, mock_get_manager, mock_pdf_extract):
        """Test history with special characters and markdown."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Response"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # History with special characters and markdown
        previous_history = (
            "**Question:** What's the significance of *italics* and **bold**?\n\n"
            "**Response:** The `code` uses special chars: < > & \" '..."
        )
        
        # Call function
        result = custom_query_func(
            custom_prompt='Follow-up question',
            filename='chapter.pdf',
            start_page=1,
            directory='/test/dir',
            include_history=True,
            history=previous_history
        )
        
        # Verify special characters are preserved in prompt
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert previous_history in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_history_with_include_query_flag(self, mock_get_manager, mock_pdf_extract):
        """Test that history works correctly with include_query flag."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Follow-up response"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        previous_history = "**Question:** First question\n\n**Response:** First response"
        
        # Call function with both history and include_query
        result = custom_query_func(
            custom_prompt='Second question',
            filename='chapter.pdf',
            start_page=1,
            directory='/test/dir',
            include_history=True,
            history=previous_history,
            include_query=True
        )
        
        # Verify output is formatted with the question
        assert "**Question:** Second question" in result
        assert "**Response:** Follow-up response" in result
        
        # Verify history was included in prompt
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert previous_history in prompt_arg


@pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")
class TestLLMPDFReviewHistory:
    """Test llm_pdf_review with history parameters."""
    
    def setup_method(self):
        """Reset LLM manager before each test."""
        reset_llm_manager()
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_pdf_review_history_disabled_by_default(self, mock_get_manager, mock_pdf_extract):
        """Test that llm_pdf_review doesn't include history by default."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Summary without history"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Document text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        pdf_review_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_pdf_review"
        )
        
        # Call function without history parameters
        result = pdf_review_func(
            filename='chapter.pdf',
            directory='/test/dir',
            review_type='summary'
        )
        
        # Verify result
        assert result == "Summary without history"
        
        # Verify the prompt does NOT contain history
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert "## Previous Conversation" not in prompt_arg
        assert "## Document Content" in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_pdf_review_history_enabled(self, mock_get_manager, mock_pdf_extract):
        """Test that llm_pdf_review includes history when enabled."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Summary building on previous analysis"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Document text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        pdf_review_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_pdf_review"
        )
        
        # Previous summary
        previous_summary = "Previous summary identified three key themes: A, B, and C."
        
        # Call function with history enabled
        result = pdf_review_func(
            filename='chapter.pdf',
            directory='/test/dir',
            review_type='summary',
            include_history=True,
            history=previous_summary
        )
        
        # Verify result
        assert result == "Summary building on previous analysis"
        
        # Verify the prompt DOES contain history
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert "## Previous Conversation" in prompt_arg
        assert previous_summary in prompt_arg
        assert "## Document Content" in prompt_arg
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_pdf_review_with_questions_and_summary_history(self, mock_get_manager, mock_pdf_extract):
        """Test using summary as context for generating questions."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Questions that build on the summary"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        pdf_review_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_pdf_review"
        )
        
        # Use summary as context for questions
        summary_history = (
            "Summary: The chapter presents a novel machine learning approach "
            "with three main contributions: improved accuracy, reduced training time, "
            "and better generalization."
        )
        
        # Generate questions with summary as context
        result = pdf_review_func(
            filename='chapter.pdf',
            directory='/test/dir',
            review_type='questions',
            include_history=True,
            history=summary_history
        )
        
        # Verify the prompt includes the summary
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        assert summary_history in prompt_arg
        assert "three main contributions" in prompt_arg


@pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")
class TestHistoryPromptFormatting:
    """Test the formatting of prompts with history."""
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_prompt_section_order(self, mock_get_manager, mock_pdf_extract):
        """Test that prompt sections appear in correct order."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Response"
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "CHAPTER_TEXT"
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call with history
        custom_query_func(
            custom_prompt='CURRENT_QUESTION',
            filename='chapter.pdf',
            directory='/test/dir',
            include_history=True,
            history='PREVIOUS_HISTORY'
        )
        
        # Check section order in prompt
        call_args = mock_manager.call.call_args
        prompt_arg = call_args[1]['prompt']
        
        # Find positions of each section
        history_pos = prompt_arg.find("PREVIOUS_HISTORY")
        chapter_pos = prompt_arg.find("CHAPTER_TEXT")
        question_pos = prompt_arg.find("CURRENT_QUESTION")
        
        # Verify order: History < Chapter < Question
        assert history_pos < chapter_pos < question_pos
        
        # Verify section headers
        assert "## Previous Conversation" in prompt_arg
        assert "## Chapter Content" in prompt_arg
        assert "## Current Question" in prompt_arg
        
        # Verify separators
        assert "---" in prompt_arg


# Mark all tests as requiring LLM dependencies
pytestmark = pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")

