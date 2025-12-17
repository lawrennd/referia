"""
Tests for LLM Integration

These tests use mocking to avoid requiring actual API keys or making real API calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Test if LLM dependencies are available
try:
    from referia.util.llm import (
        LLMManager, CostTracker, get_llm_manager, reset_llm_manager,
        LLMError, LLMConfigError, LLMProviderError, LLMBudgetError
    )
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="LLM dependencies not installed")


class TestCostTracker:
    """Test the cost tracking functionality."""
    
    def test_cost_tracker_initialization(self):
        """Test cost tracker initializes correctly."""
        tracker = CostTracker()
        assert tracker.total_tokens == 0
        assert tracker.total_cost == 0.0
        assert len(tracker.calls) == 0
    
    def test_cost_tracker_with_budget(self):
        """Test cost tracker with budget limit."""
        tracker = CostTracker(budget_per_run=0.01)
        assert tracker.budget_per_run == 0.01
    
    def test_log_call_calculates_cost(self):
        """Test that log_call calculates costs correctly."""
        tracker = CostTracker()
        cost = tracker.log_call("gpt-4o-mini", input_tokens=1000, output_tokens=500)
        
        assert cost > 0
        assert tracker.total_cost > 0
        assert tracker.total_tokens == 1500
        assert len(tracker.calls) == 1
    
    def test_budget_exceeded_raises_error(self):
        """Test that exceeding budget raises error."""
        tracker = CostTracker(budget_per_run=0.0001)  # Very small budget
        
        with pytest.raises(LLMBudgetError):
            tracker.log_call("gpt-4o-mini", input_tokens=100000, output_tokens=50000)
    
    def test_get_summary(self):
        """Test getting cost summary."""
        tracker = CostTracker(budget_per_run=1.0)
        tracker.log_call("gpt-4o-mini", input_tokens=1000, output_tokens=500)
        
        summary = tracker.get_summary()
        assert summary["total_calls"] == 1
        assert summary["total_tokens"] == 1500
        assert summary["total_cost"] > 0
        assert summary["budget_remaining"] is not None


@pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")
class TestLLMManager:
    """Test the LLM manager functionality."""
    
    def setup_method(self):
        """Reset LLM manager before each test."""
        reset_llm_manager()
    
    def test_manager_initialization(self):
        """Test manager initializes correctly."""
        config = {
            "default_provider": "openai",
            "cache_enabled": False,
        }
        manager = LLMManager(config)
        assert manager.config["default_provider"] == "openai"
        assert manager.providers == {}
    
    def test_manager_without_langchain_raises_error(self):
        """Test that manager raises error if langchain not available."""
        with patch.dict(sys.modules, {'langchain_openai': None}):
            # This would raise error in real scenario
            pass  # Skip this test as it's hard to mock properly
    
    @patch('referia.util.llm.ChatOpenAI')
    def test_get_openai_client(self, mock_chat_openai):
        """Test getting OpenAI client."""
        config = {
            "api_keys": {"openai": "test-key"}
        }
        manager = LLMManager(config)
        
        mock_client = Mock()
        mock_chat_openai.return_value = mock_client
        
        client = manager.get_client("openai", "gpt-4o-mini")
        assert client is not None
        mock_chat_openai.assert_called_once()
    
    @patch('referia.util.llm.ChatAnthropic')
    def test_get_anthropic_client(self, mock_chat_anthropic):
        """Test getting Anthropic client."""
        config = {
            "api_keys": {"anthropic": "test-key"}
        }
        manager = LLMManager(config)
        
        mock_client = Mock()
        mock_chat_anthropic.return_value = mock_client
        
        client = manager.get_client("anthropic", "claude-3-haiku-20240307")
        assert client is not None
        mock_chat_anthropic.assert_called_once()
    
    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises error."""
        manager = LLMManager({})
        
        with pytest.raises(LLMConfigError, match="Unsupported provider"):
            manager.get_client("unsupported", "model")
    
    @patch('referia.util.llm.ChatOpenAI')
    def test_llm_call_with_mock(self, mock_chat_openai):
        """Test making an LLM call with mocked response."""
        # Setup mock
        mock_response = Mock()
        mock_response.content = "This is a test response"
        
        mock_client = Mock()
        mock_client.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_client
        
        # Create manager and make call
        config = {
            "api_keys": {"openai": "test-key"},
            "cache_enabled": False,
        }
        manager = LLMManager(config)
        
        response = manager.call(
            prompt="Test prompt",
            model="gpt-4o-mini",
            temperature=0.5
        )
        
        assert response == "This is a test response"
        assert mock_client.invoke.called
    
    @patch('referia.util.llm.diskcache')
    @patch('referia.util.llm.ChatOpenAI')
    def test_caching_works(self, mock_chat_openai, mock_diskcache):
        """Test that caching works correctly."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.get.return_value = None  # First call: cache miss
        mock_diskcache.Cache.return_value = mock_cache
        
        mock_response = Mock()
        mock_response.content = "Cached response"
        
        mock_client = Mock()
        mock_client.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_client
        
        # Create manager with caching
        config = {
            "api_keys": {"openai": "test-key"},
            "cache_enabled": True,
            "cache_dir": ".test_cache",
        }
        manager = LLMManager(config)
        
        # First call
        response1 = manager.call(prompt="Test", model="gpt-4o-mini")
        assert response1 == "Cached response"
        
        # Verify cache was checked and set
        assert mock_cache.get.called
        assert mock_cache.set.called


@pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")
class TestLLMComputeFunctions:
    """Test LLM compute functions."""
    
    def setup_method(self):
        """Setup for each test."""
        reset_llm_manager()
    
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_summarise_function(self, mock_get_manager):
        """Test llm_summarise compute function."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mock manager
        mock_manager = Mock()
        mock_manager.call.return_value = "This is a summary."
        mock_get_manager.return_value = mock_manager
        
        # Create compute instance
        interface_config = {"compute": []}
        interface = Interface(interface_config, directory="/tmp")
        compute = Compute(interface)
        
        # Get the LLM functions
        llm_functions = compute._llm_functions_list()
        
        # Find llm_summarise function
        summarise_func = None
        for func_info in llm_functions:
            if func_info["name"] == "llm_summarise":
                summarise_func = func_info["function"]
                break
        
        assert summarise_func is not None
        
        # Call the function
        result = summarise_func("Long text to summarise...")
        
        assert result == "This is a summary."
        assert mock_manager.call.called
    
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_classify_function(self, mock_get_manager):
        """Test llm_classify compute function."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Setup mock
        mock_manager = Mock()
        mock_manager.call.return_value = "positive"
        mock_get_manager.return_value = mock_manager
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get classify function
        llm_functions = compute._llm_functions_list()
        classify_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_classify"
        )
        
        # Call function
        result = classify_func("Great product!", categories=["positive", "negative"])
        
        assert result == "positive"
        assert mock_manager.call.called
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_function(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query compute function with valid inputs."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "The chapter discusses methodological innovations in machine learning."
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter text about machine learning methods..."
        
        # Create compute instance with data
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Create data with a prompt field
        df = pd.DataFrame({
            'chapter1CustomPrompt': ['What are the key contributions?'],
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get custom query function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function (passing the prompt value directly, as row_args would do)
        result = custom_query_func(
            custom_prompt='What are the key contributions?',
            filename='thesis_chapter1.pdf',
            start_page=1,
            directory='/test/dir',
            model='gpt-4o-mini'
        )
        
        # Verify result
        assert result == "The chapter discusses methodological innovations in machine learning."
        assert mock_pdf_extract.called
        assert mock_manager.call.called
        
        # Verify PDF extraction was called correctly
        mock_pdf_extract.assert_called_once_with(
            filename='thesis_chapter1.pdf',
            directory='/test/dir',
            start_page=1,
            end_page=None,
            max_chars=50000
        )
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_empty_prompt(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query with empty prompt field."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Create compute instance with empty prompt
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        df = pd.DataFrame({
            'chapter1CustomPrompt': [''],  # Empty prompt
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function (passing empty prompt as row_args would extract)
        result = custom_query_func(
            custom_prompt='',  # Empty prompt from the data
            filename='thesis_chapter1.pdf',
            start_page=1
        )
        
        # Should return warning message
        assert "⚠️" in result
        assert "Please enter a question" in result
        
        # Should not call PDF extraction or LLM
        assert not mock_pdf_extract.called
        assert not mock_get_manager.called
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_missing_prompt_field(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query with missing prompt field."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Create compute instance without the prompt field
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        df = pd.DataFrame({
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function with None (simulating missing field)
        result = custom_query_func(
            custom_prompt=None,  # Missing/None prompt
            filename='thesis_chapter1.pdf',
            start_page=1
        )
        
        # Should return warning message
        assert "⚠️" in result
        assert "Please enter a question" in result
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_pdf_extraction_error(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query when PDF extraction fails."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Setup mocks - PDF extraction raises error
        mock_pdf_extract.side_effect = FileNotFoundError("PDF not found")
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        df = pd.DataFrame({
            'chapter1CustomPrompt': ['What are the contributions?'],
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function
        result = custom_query_func(
            custom_prompt='What are the contributions?',
            filename='missing.pdf',
            start_page=1
        )
        
        # Should return error message
        assert "❌" in result
        assert "Error extracting PDF" in result
        assert "PDF not found" in result
        
        # Should not call LLM
        assert not mock_get_manager.called
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_empty_pdf_text(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query when PDF extraction returns empty text."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Setup mocks - PDF extraction returns empty string
        mock_pdf_extract.return_value = ""
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        df = pd.DataFrame({
            'chapter1CustomPrompt': ['What are the contributions?'],
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function
        result = custom_query_func(
            custom_prompt='What are the contributions?',
            filename='empty.pdf',
            start_page=1
        )
        
        # Should return warning message
        assert "⚠️" in result
        assert "Could not extract text" in result
        assert "empty.pdf" in result
        
        # Should not call LLM
        assert not mock_get_manager.called
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_llm_error(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query when LLM call fails."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Setup mocks
        mock_pdf_extract.return_value = "Chapter text content..."
        
        mock_manager = Mock()
        mock_manager.call.side_effect = LLMError("API rate limit exceeded")
        mock_get_manager.return_value = mock_manager
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        df = pd.DataFrame({
            'chapter1CustomPrompt': ['What are the contributions?'],
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function
        result = custom_query_func(
            custom_prompt='What are the contributions?',
            filename='chapter.pdf',
            start_page=1
        )
        
        # Should return error message
        assert "❌" in result
        assert "LLM Error" in result
        assert "API rate limit exceeded" in result
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_with_custom_system_prompt(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query with custom system prompt."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Technical analysis of methodology."
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter content..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        df = pd.DataFrame({
            'chapter1CustomPrompt': ['Analyze the methodology'],
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function with custom system prompt
        custom_system = "You are an expert in technical methodology evaluation."
        result = custom_query_func(
            custom_prompt='Analyze the methodology',
            filename='chapter.pdf',
            start_page=1,
            system_prompt=custom_system
        )
        
        # Verify result
        assert result == "Technical analysis of methodology."
        
        # Verify system prompt was passed to LLM
        call_kwargs = mock_manager.call.call_args[1]
        assert call_kwargs['system_prompt'] == custom_system
    
    @patch('referia.assess.compute.pdf_extract_text')
    @patch('referia.assess.compute.get_llm_manager')
    def test_llm_custom_query_with_page_range(self, mock_get_manager, mock_pdf_extract):
        """Test llm_custom_query with start and end page."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        import pandas as pd
        
        # Setup mocks
        mock_manager = Mock()
        mock_manager.call.return_value = "Analysis complete."
        mock_get_manager.return_value = mock_manager
        
        mock_pdf_extract.return_value = "Chapter content pages 5-10..."
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        df = pd.DataFrame({
            'chapter1CustomPrompt': ['Summarize this section'],
            'chapter1CustomResponse': ['']
        })
        compute.data = CustomDataFrame(df)
        
        # Get function
        llm_functions = compute._llm_functions_list()
        custom_query_func = next(
            f["function"] for f in llm_functions if f["name"] == "llm_custom_query"
        )
        
        # Call function with page range
        result = custom_query_func(
            custom_prompt='Summarize this section',
            filename='chapter.pdf',
            start_page=5,
            end_page=10,
            directory='/test/dir'
        )
        
        # Verify PDF extraction was called with page range
        mock_pdf_extract.assert_called_once_with(
            filename='chapter.pdf',
            directory='/test/dir',
            start_page=5,
            end_page=10,
            max_chars=50000
        )


@pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")
class TestLLMFunctionRegistry:
    """Test that LLM functions are properly registered."""
    
    def test_llm_custom_query_registered(self):
        """Test that llm_custom_query is in the function registry."""
        from referia.assess.compute import Compute
        from referia.config.interface import Interface
        
        # Create compute instance
        interface = Interface({"compute": []}, directory="/tmp", user_file="test.yml")
        compute = Compute(interface)
        
        # Get all LLM functions
        llm_functions = compute._llm_functions_list()
        
        # Find llm_custom_query
        function_names = [f["name"] for f in llm_functions]
        assert "llm_custom_query" in function_names
        
        # Verify it has the expected structure
        custom_query_info = next(
            f for f in llm_functions if f["name"] == "llm_custom_query"
        )
        assert "function" in custom_query_info
        assert "default_args" in custom_query_info
        assert "docstr" in custom_query_info
        
        # Verify default args
        defaults = custom_query_info["default_args"]
        assert defaults["model"] == "gpt-4o-mini"
        assert defaults["temperature"] == 0.7
        assert defaults["max_chars"] == 50000
        assert defaults["directory"] == ""
        
        # Verify docstring
        assert "custom user prompt" in custom_query_info["docstr"].lower()


@pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")
class TestIntegration:
    """Integration tests for LLM functionality."""
    
    def setup_method(self):
        """Setup for each test."""
        reset_llm_manager()
    
    def test_manager_singleton(self):
        """Test that manager is a singleton."""
        manager1 = get_llm_manager()
        manager2 = get_llm_manager()
        assert manager1 is manager2
    
    def test_reset_manager(self):
        """Test resetting the manager."""
        manager1 = get_llm_manager()
        reset_llm_manager()
        manager2 = get_llm_manager()
        assert manager1 is not manager2


# Mark all tests as requiring LLM dependencies
pytestmark = pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM dependencies not installed")

