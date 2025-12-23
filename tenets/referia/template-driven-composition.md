---
id: "template-driven-composition"
title: "Template-Driven Interface Composition"
created: "2025-12-23"
last_updated: "2025-12-23"
version: "1.0"
tags:
- tenet
- templates
- composition
- configuration
- reusability
---

# Template-Driven Interface Composition

## Tenet

**Description**: Review interfaces should be built from reusable, composable patterns rather than through repetition or hardcoded expansion logic. When reviewers need similar structures repeated (chapters, criteria, sections), they should define the pattern once and instantiate it multiple times with different values. These patterns should compose—complex interfaces built from simpler building blocks—enabling sophisticated workflows without proportional complexity growth. The system should handle mechanical aspects (repeated structure, supporting metadata) automatically while keeping the review structure explicit and under user control. This approach should be accessible to non-programmers through declarative configuration rather than requiring code changes.

**Quote**: *"Define once, instantiate many, compose deeply"*

**Examples**:
- Defining one chapter review pattern and applying it to 10 chapters
- Building complex review sections from simpler reusable components
- Providing a library of common review patterns that users can instantiate
- Parameterising patterns so the same structure works for different content
- Automatically generating supporting metadata (timestamps, status fields) from structure
- Enabling pattern definition through configuration rather than code
- Detecting and preventing invalid compositions (circular references)
- Making review structure explicit and visible in configuration

**Counter-examples**:
- Repeating similar configurations manually for each item
- Building expansion logic into code rather than configuration
- No mechanism for reusing common patterns across reviews
- Requiring manual specification of all supporting metadata
- Patterns that can't be combined to build more complex structures
- Forcing users to write code to create new review structures

**Conflicts**:
- **vs Simplicity**: When pattern abstraction adds cognitive overhead for straightforward cases
- Resolution: Support both direct specification for simple cases and patterns for complex repeated structures
- **vs Flexibility**: When patterns constrain expression of unique requirements
- Resolution: Patterns should be convenience, not constraint—always allow direct specification when needed

