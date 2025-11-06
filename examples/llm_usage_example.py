"""
Example: Using LLM Integration in Referia
==========================================

This example demonstrates how to use LLM capabilities programmatically.

Prerequisites:
    1. Install LLM dependencies: 
       poetry install --with llm
    
    2. Set API key:
       export OPENAI_API_KEY="your-key-here"
       # OR
       export ANTHROPIC_API_KEY="your-key-here"

Usage:
    python examples/llm_usage_example.py
"""

import os
from referia.util.llm import get_llm_manager, reset_llm_manager

def example_basic_usage():
    """Example 1: Basic LLM call"""
    print("=" * 60)
    print("Example 1: Basic LLM Usage")
    print("=" * 60)
    
    # Get the LLM manager
    manager = get_llm_manager()
    
    # Make a simple call
    response = manager.call(
        prompt="Explain what a code review is in one sentence.",
        model="gpt-4o-mini",
        temperature=0.3
    )
    
    print(f"Response: {response}\n")
    
    # Check costs
    summary = manager.get_cost_summary()
    print(f"Cost Summary: {summary}\n")


def example_with_system_prompt():
    """Example 2: Using system prompts"""
    print("=" * 60)
    print("Example 2: Using System Prompts")
    print("=" * 60)
    
    manager = get_llm_manager()
    
    response = manager.call(
        prompt="Review this code: def add(a,b): return a+b",
        model="gpt-4o-mini",
        temperature=0.5,
        system_prompt="You are an expert code reviewer. Provide constructive feedback."
    )
    
    print(f"Response: {response}\n")


def example_with_configuration():
    """Example 3: Using custom configuration"""
    print("=" * 60)
    print("Example 3: Custom Configuration")
    print("=" * 60)
    
    # Reset manager to apply new config
    reset_llm_manager()
    
    config = {
        "default_provider": "openai",
        "default_model": "gpt-4o-mini",
        "cache_enabled": True,
        "cache_dir": ".example_cache",
        "cache_ttl": 3600,
        "budget_per_run": 0.10,  # $0.10 limit
        "retry_attempts": 3,
    }
    
    manager = get_llm_manager(config)
    
    # This call will be cached
    response1 = manager.call(
        prompt="What is Python?",
        model="gpt-4o-mini",
        temperature=0.3
    )
    print(f"First call: {response1[:100]}...\n")
    
    # This should hit the cache
    response2 = manager.call(
        prompt="What is Python?",
        model="gpt-4o-mini",
        temperature=0.3
    )
    print(f"Second call (cached): {response2[:100]}...\n")
    print(f"Responses match: {response1 == response2}\n")
    
    # Show cost summary
    summary = manager.get_cost_summary()
    print(f"Cost Summary: {summary}\n")


def example_with_compute_framework():
    """Example 4: Using LLM with compute framework"""
    print("=" * 60)
    print("Example 4: Compute Framework Integration")
    print("=" * 60)
    
    from referia.assess.compute import Compute
    from referia.config.interface import Interface
    from lynguine.assess.data import CustomDataFrame
    import pandas as pd
    
    # Create sample data
    data_dict = {
        "review_text": [
            "This paper presents a novel approach to machine learning. The methodology is sound and results are impressive.",
            "The paper lacks clarity in explaining the core concepts. More examples would help.",
            "Excellent work with thorough experiments. Minor issues with notation in section 3."
        ]
    }
    
    # Create interface configuration
    interface_config = {
        "llm": {
            "default_provider": "openai",
            "default_model": "gpt-4o-mini",
            "cache_enabled": True,
        },
        "compute": [
            {
                "function": "llm_summarise",
                "field": "summary",
                "row_args": {
                    "text": "review_text"
                },
                "args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.3,
                    "max_tokens": 50
                }
            },
            {
                "function": "llm_classify",
                "field": "sentiment",
                "row_args": {
                    "text": "review_text"
                },
                "args": {
                    "categories": ["positive", "negative", "neutral"],
                    "model": "gpt-4o-mini"
                }
            }
        ]
    }
    
    # Create components
    interface = Interface(interface_config)
    compute = Compute(interface)
    data = CustomDataFrame(data=pd.DataFrame(data_dict))
    
    # Run computations
    print("Running LLM computations on review data...\n")
    compute.run_all(data, interface)
    
    # Display results
    print("Results:")
    for idx in data.index:
        data.set_index(idx)
        print(f"\nReview {idx + 1}:")
        print(f"  Original: {data.get_value_column('review_text')[:60]}...")
        print(f"  Summary: {data.get_value_column('summary')}")
        print(f"  Sentiment: {data.get_value_column('sentiment')}")


def example_anthropic():
    """Example 5: Using Anthropic (Claude)"""
    print("=" * 60)
    print("Example 5: Using Anthropic/Claude")
    print("=" * 60)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Skipping: ANTHROPIC_API_KEY not set\n")
        return
    
    reset_llm_manager()
    manager = get_llm_manager()
    
    response = manager.call(
        prompt="Explain quantum computing in simple terms.",
        model="claude-3-haiku-20240307",
        temperature=0.5,
        max_tokens=100
    )
    
    print(f"Claude Response: {response}\n")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Referia LLM Integration Examples")
    print("=" * 60 + "\n")
    
    # Check if API keys are available
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        print("ERROR: No API keys found!")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        return
    
    try:
        # Run examples
        example_basic_usage()
        example_with_system_prompt()
        example_with_configuration()
        
        # This example requires pandas and other dependencies
        try:
            example_with_compute_framework()
        except Exception as e:
            print(f"Skipping compute framework example: {e}\n")
        
        example_anthropic()
        
        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure you have:")
        print("  1. Installed LLM dependencies: poetry install --with llm")
        print("  2. Set API key: export OPENAI_API_KEY='your-key'")
        raise


if __name__ == "__main__":
    main()

