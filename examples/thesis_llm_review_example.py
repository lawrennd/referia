#!/usr/bin/env python
"""
Example: Programmatic LLM-Based Thesis Review

This script demonstrates how to use the LLM+PDF integration to
automatically generate initial reviews for thesis chapters.
"""

import pandas as pd
from referia.assess.compute import Compute
from referia.config.interface import Interface
from lynguine.assess.data import CustomDataFrame

# Setup: Make sure you have:
# 1. Installed LLM dependencies: poetry install --with llm
# 2. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file

print("=== Thesis Chapter LLM Review Example ===\n")

# Sample thesis data
thesis_data = pd.DataFrame({
    "Name": ["Smith_J", "Jones_M"],
    "Ch1FP": [1, 1],  # Chapter 1 first page
    "Ch2FP": [15, 20],  # Chapter 2 first page
})

# Interface configuration with LLM
config = {
    "llm": {
        "default_provider": "openai",
        "default_model": "gpt-4o-mini",
        "cache_enabled": True,
        "budget_per_run": 1.00,  # $1 budget for this example
    },
    "compute": [
        # Example 1: General review of Chapter 1
        {
            "function": "llm_pdf_review",
            "field": "ch1_general",
            "view_args": {
                "filename": {
                    "display": "{Name}_thesis_ch1.pdf"
                }
            },
            "args": {
                "directory": "$HOME/Documents/theses/examined",
                "review_type": "general",
                "model": "gpt-4o-mini",
                "max_chars": 30000,
            }
        },
        
        # Example 2: Strengths of Chapter 1
        {
            "function": "llm_pdf_review",
            "field": "ch1_strengths",
            "view_args": {
                "filename": {
                    "display": "{Name}_thesis_ch1.pdf"
                }
            },
            "args": {
                "directory": "$HOME/Documents/theses/examined",
                "review_type": "strengths",
                "model": "gpt-4o-mini",
            }
        },
        
        # Example 3: Technical assessment of Chapter 2
        {
            "function": "llm_pdf_review",
            "field": "ch2_technical",
            "view_args": {
                "filename": {
                    "display": "{Name}_thesis_ch2.pdf"
                }
            },
            "args": {
                "directory": "$HOME/Documents/theses/examined",
                "review_type": "technical",
                "model": "gpt-4o-mini",
            }
        },
        
        # Example 4: Custom system prompt
        {
            "function": "llm_pdf_review",
            "field": "ch1_methodology",
            "view_args": {
                "filename": {
                    "display": "{Name}_thesis_ch1.pdf"
                }
            },
            "args": {
                "directory": "$HOME/Documents/theses/examined",
                "model": "gpt-4o-mini",
                "system_prompt": """
                You are reviewing a thesis introduction chapter. Focus on:
                1. Research question clarity
                2. Literature review completeness
                3. Contribution statement
                Provide specific, constructive feedback in under 150 words.
                """
            }
        },
    ]
}

# Create temporary user file for Interface
import yaml
import tempfile
import os

user_config = {
    "name": "Thesis Reviewer",
    "email": "reviewer@university.edu"
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
    yaml.dump(user_config, f)
    user_file = f.name

try:
    # Initialize interface and compute
    interface = Interface(config, directory=".", user_file=user_file)
    compute = Compute(interface)
    data = CustomDataFrame(data=thesis_data)
    
    print("Running LLM-based chapter reviews...")
    print("(This will make API calls if the PDF files exist)\n")
    
    # Run all computations
    compute.run_all(data, interface)
    
    # Display results
    print("\n=== Generated Reviews ===\n")
    
    for idx in data.index:
        data.set_index(idx)
        name = data.get_value_column("Name")
        
        print(f"Candidate: {name}")
        print("-" * 60)
        
        # Show generated reviews if they exist
        for field in ["ch1_general", "ch1_strengths", "ch2_technical", "ch1_methodology"]:
            try:
                review = data.get_value_column(field)
                if review and not pd.isna(review):
                    print(f"\n{field}:")
                    print(review)
            except:
                pass
        
        print("\n" + "=" * 60 + "\n")
    
    # Show cost summary
    print("\n=== Cost Summary ===")
    from referia.util.llm import get_llm_manager
    manager = get_llm_manager()
    summary = manager.get_cost_summary()
    
    print(f"Total API calls:  {summary['total_calls']}")
    print(f"Total cost:       ${summary['total_cost']:.4f}")
    print(f"Budget remaining: ${summary.get('budget_remaining', 'N/A')}")
    
finally:
    # Cleanup
    os.unlink(user_file)

print("\n=== Tips for Production Use ===")
print("""
1. Start with 'summary' review_type to get oriented
2. Use 'general' for balanced initial reviews
3. Combine with pdf_extract_comments for your manual annotations
4. Always review and edit LLM output - it's a starting point
5. Use max_chars=30000 for long chapters to stay within context limits
6. Set appropriate budgets to control costs
7. Enable caching to reduce costs for repeated reviews
8. Consider using gpt-4o-mini for cost-effective reviews
""")

