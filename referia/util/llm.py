"""
LLM Integration for Referia Compute Framework

This module provides Large Language Model capabilities for the referia compute framework.
It manages connections to various LLM providers (OpenAI, Anthropic) with retry logic,
caching, cost tracking, and error handling.

Usage:
    from referia.util.llm import LLMManager, get_llm_manager
    
    # Get the singleton manager
    manager = get_llm_manager()
    
    # Make an LLM call
    response = manager.call(
        prompt="Summarise this text: ...",
        model="gpt-4o-mini",
        temperature=0.3
    )
"""

import os
import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache

# LLM imports with graceful fallback if not installed
try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None
    ChatAnthropic = None
    HumanMessage = None
    SystemMessage = None
    AIMessage = None

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    retry = None
    stop_after_attempt = None
    wait_exponential = None
    retry_if_exception_type = None

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False
    diskcache = None


logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMConfigError(LLMError):
    """Exception raised for LLM configuration errors."""
    pass


class LLMProviderError(LLMError):
    """Exception raised when LLM provider encounters an error."""
    pass


class LLMBudgetError(LLMError):
    """Exception raised when budget limits are exceeded."""
    pass


class CostTracker:
    """Track LLM costs and enforce budgets."""
    
    # Approximate token costs per 1M tokens (as of 2025-11-06)
    COSTS = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }
    
    def __init__(self, budget_per_run: Optional[float] = None):
        """
        Initialize cost tracker.
        
        Args:
            budget_per_run: Maximum budget per run in dollars
        """
        self.total_tokens = 0
        self.total_cost = 0.0
        self.budget_per_run = budget_per_run
        self.calls = []
        
    def log_call(self, model: str, input_tokens: int, output_tokens: int, 
                 response_text: str = "") -> float:
        """
        Log an LLM call and calculate cost.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            response_text: Response text (for debugging)
            
        Returns:
            Cost of this call in dollars
            
        Raises:
            LLMBudgetError: If budget is exceeded
        """
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        self.total_tokens += input_tokens + output_tokens
        self.total_cost += cost
        
        self.calls.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "response_length": len(response_text)
        })
        
        logger.info(
            f"LLM call: model={model}, "
            f"tokens={input_tokens + output_tokens}, "
            f"cost=${cost:.4f}, "
            f"total_cost=${self.total_cost:.4f}"
        )
        
        if self.budget_per_run and self.total_cost > self.budget_per_run:
            raise LLMBudgetError(
                f"Budget exceeded: ${self.total_cost:.2f} > ${self.budget_per_run:.2f}"
            )
        
        return cost
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a model call."""
        if model not in self.COSTS:
            logger.warning(f"Unknown model {model}, using default pricing")
            # Default to gpt-4o-mini pricing
            model = "gpt-4o-mini"
        
        costs = self.COSTS[model]
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of costs and usage."""
        return {
            "total_calls": len(self.calls),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "budget_remaining": (
                self.budget_per_run - self.total_cost 
                if self.budget_per_run else None
            ),
        }


class LLMManager:
    """
    Manage LLM connections and calls with retry logic, caching, and cost tracking.
    
    This class provides a unified interface for calling different LLM providers
    with automatic retry, caching, and cost tracking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM manager.
        
        Args:
            config: Configuration dictionary with keys:
                - default_provider: Default LLM provider ('openai' or 'anthropic')
                - default_model: Default model name
                - api_keys: Dictionary of provider API keys
                - cache_enabled: Whether to enable caching
                - cache_dir: Directory for cache storage
                - budget_per_run: Budget limit per run
                - retry_attempts: Maximum retry attempts
                - retry_backoff: Backoff factor for retries
        """
        if not LANGCHAIN_AVAILABLE:
            raise LLMConfigError(
                "LangChain is not installed. Install with: poetry install --with llm"
            )
        
        self.config = config or {}
        self.providers = {}
        self.cost_tracker = CostTracker(
            budget_per_run=self.config.get("budget_per_run")
        )
        
        # Cache setup
        self.cache_enabled = self.config.get("cache_enabled", True)
        if self.cache_enabled and DISKCACHE_AVAILABLE:
            cache_dir = self.config.get("cache_dir", ".llm_cache")
            self.cache = diskcache.Cache(cache_dir)
            logger.info(f"LLM cache enabled at {cache_dir}")
        else:
            self.cache = None
            if self.cache_enabled and not DISKCACHE_AVAILABLE:
                logger.warning(
                    "Cache requested but diskcache not available. "
                    "Install with: poetry install --with llm"
                )
        
        # Retry configuration
        self.retry_attempts = self.config.get("retry_attempts", 3)
        self.retry_backoff = self.config.get("retry_backoff", 2)
        
        logger.info("LLMManager initialized")
    
    def get_client(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        """
        Get or create an LLM client for the specified provider.
        
        Args:
            provider: Provider name ('openai' or 'anthropic')
            model: Model name
            
        Returns:
            LLM client instance
            
        Raises:
            LLMConfigError: If provider is not supported or API key missing
        """
        cache_key = f"{provider}:{model}"
        
        if cache_key in self.providers:
            return self.providers[cache_key]
        
        # Get API key from config or environment
        api_keys = self.config.get("api_keys", {})
        
        if provider == "openai":
            api_key = api_keys.get("openai") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise LLMConfigError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                    "or provide in config."
                )
            client = ChatOpenAI(model=model, api_key=api_key)
            
        elif provider == "anthropic":
            api_key = api_keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise LLMConfigError(
                    "Anthropic API key not found. Set ANTHROPIC_API_KEY environment "
                    "variable or provide in config."
                )
            client = ChatAnthropic(model=model, api_key=api_key)
            
        else:
            raise LLMConfigError(f"Unsupported provider: {provider}")
        
        self.providers[cache_key] = client
        logger.info(f"Created {provider} client for model {model}")
        return client
    
    def _make_cache_key(self, messages: List, model: str, **kwargs) -> str:
        """Create a cache key for the request."""
        import hashlib
        import json
        
        # Convert messages to serializable format
        msg_strs = []
        for msg in messages:
            if hasattr(msg, "content"):
                msg_strs.append(f"{msg.__class__.__name__}:{msg.content}")
            else:
                msg_strs.append(str(msg))
        
        key_data = {
            "messages": msg_strs,
            "model": model,
            **kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def call(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """
        Make an LLM call with automatic retry and caching.
        
        Args:
            prompt: User prompt
            model: Model name
            provider: Provider name (auto-detected from model if not specified)
            system_prompt: System prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            use_cache: Whether to use caching for this call
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            Response text from the LLM
            
        Raises:
            LLMProviderError: If the LLM call fails after retries
        """
        # Auto-detect provider from model name
        if provider is None:
            if "gpt" in model.lower():
                provider = "openai"
            elif "claude" in model.lower():
                provider = "anthropic"
            else:
                provider = self.config.get("default_provider", "openai")
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        # Check cache
        cache_key = None
        if use_cache and self.cache:
            cache_key = self._make_cache_key(messages, model, temperature=temperature)
            cached_response = self.cache.get(cache_key)
            if cached_response is not None:
                logger.info(f"Cache hit for model {model}")
                return cached_response
        
        # Make the call with retry logic
        try:
            response = self._call_with_retry(
                provider, model, messages, temperature, max_tokens, **kwargs
            )
            response_text = response.content
            
            # Track cost (approximate based on character count)
            # Note: Actual token counting would require tokenizer
            input_tokens = len(prompt) // 4  # Rough approximation
            output_tokens = len(response_text) // 4
            if system_prompt:
                input_tokens += len(system_prompt) // 4
            
            self.cost_tracker.log_call(model, input_tokens, output_tokens, response_text)
            
            # Cache the response
            if use_cache and self.cache and cache_key:
                ttl = self.config.get("cache_ttl", 3600)  # Default 1 hour
                self.cache.set(cache_key, response_text, expire=ttl)
                logger.debug(f"Cached response for {cache_key}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise LLMProviderError(f"Failed to call {provider} model {model}: {e}")
    
    def _call_with_retry(
        self, 
        provider: str, 
        model: str, 
        messages: List, 
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ):
        """Make LLM call with retry logic."""
        client = self.get_client(provider, model)
        
        # Build kwargs for the call
        call_kwargs = {
            "temperature": temperature,
            **kwargs
        }
        if max_tokens:
            call_kwargs["max_tokens"] = max_tokens
        
        # Implement manual retry if tenacity not available
        if not TENACITY_AVAILABLE:
            import time
            last_error = None
            for attempt in range(self.retry_attempts):
                try:
                    return client.invoke(messages, **call_kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < self.retry_attempts - 1:
                        wait_time = self.retry_backoff ** attempt
                        logger.warning(
                            f"LLM call failed (attempt {attempt + 1}/{self.retry_attempts}), "
                            f"retrying in {wait_time}s: {e}"
                        )
                        time.sleep(wait_time)
            raise last_error
        else:
            # Use tenacity for retry with exponential backoff
            @retry(
                stop=stop_after_attempt(self.retry_attempts),
                wait=wait_exponential(multiplier=self.retry_backoff, min=1, max=60),
                reraise=True
            )
            def _call():
                return client.invoke(messages, **call_kwargs)
            
            return _call()
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get summary of costs and usage."""
        return self.cost_tracker.get_summary()
    
    def reset_cost_tracker(self):
        """Reset the cost tracker."""
        self.cost_tracker = CostTracker(
            budget_per_run=self.config.get("budget_per_run")
        )


# Singleton instance
_llm_manager = None


def get_llm_manager(config: Optional[Dict[str, Any]] = None) -> LLMManager:
    """
    Get the singleton LLM manager instance.
    
    Args:
        config: Configuration dictionary (only used on first call)
        
    Returns:
        LLM manager instance
    """
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager(config)
    return _llm_manager


def reset_llm_manager():
    """Reset the singleton LLM manager (useful for testing)."""
    global _llm_manager
    _llm_manager = None

