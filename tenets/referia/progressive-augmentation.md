---
id: "progressive-augmentation"
title: "Progressive Augmentation of Infrastructure"
created: "2025-12-23"
last_updated: "2025-12-23"
version: "1.0"
tags:
- tenet
- architecture
- layering
- inheritance
- lynguine-integration
---

# Progressive Augmentation of Infrastructure

## Tenet

**Description**: When referia needs behaviour that lynguine doesn't provide, it should augment infrastructure through explicit overrides and extensions rather than modifying or forking lynguine. Referia's classes inherit from lynguine and add review-specific functionality through well-documented override methods. Extensions should be tested for compatibility with lynguine updates and designed to be removable if lynguine later provides equivalent functionality. The relationship should feel like a mature inheritance hierarchy, not fragile monkey-patching. 

Implement new features in referia first to enable rapid iteration, then promote general-purpose components to lynguine once patterns are proven and stabilized. This evolutionary approach balances innovation velocity with infrastructure stability.

**Quote**: *"Extend infrastructure, don't fork it"*

**Examples**:
- `referia.assess.data.CustomDataFrame` extends `lynguine.assess.data.CustomDataFrame`
- `referia.assess.compute.Compute` extends lynguine's and adds review-specific functions
- Review-specific compute functions added to registry without modifying lynguine
- `from_flow()` override calls `super().from_flow()` then adds review-specific augmentation
- CIP-0005 documents proper layering and timing between referia and lynguine
- CIP-0006 pattern: LLM functions in referia first, promote to lynguine when general-purpose
- Template expansion in referia doesn't require lynguine changes
- Tests verify referia works correctly with lynguine updates
- Clear documentation of what's inherited vs extended

**Counter-examples**:
- Forking lynguine and modifying its code directly
- Monkey-patching lynguine classes at runtime without documentation
- Creating incompatible parallel implementations of lynguine features
- Extensions that break when lynguine is updated
- No documentation of the inheritance relationship
- Bypassing `super()` calls and duplicating lynguine code

**Conflicts**:
- **vs Development Speed**: When lynguine changes slowly or doesn't provide needed features
- Resolution: Implement in referia first for rapid iteration, promote to lynguine when patterns proven stable
- **vs Code Duplication**: When augmentation seems to require copying lynguine code
- Resolution: Minimize duplication through proper inheritance; call `super()` methods when possible; only override what's necessary

