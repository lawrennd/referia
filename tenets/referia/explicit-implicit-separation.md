---
id: "explicit-implicit-separation"
title: "Explicit Implicit Separation"
created: "2025-10-10"
last_updated: "2025-10-10"
version: "1.0"
tags:
- tenet
- separation
- layering
- architecture
---

# Explicit Implicit Separation

## Tenet

**Description**: referia should maintain clear separation between explicit infrastructure behavior and implicit application convenience. When referia needs implicit behavior, it should handle it explicitly in its own layer rather than expecting the infrastructure to become implicit. This preserves the explicit nature of the infrastructure while providing user-friendly convenience.

**Quote**: *"Handle implicit behavior explicitly in the application layer"*

**Examples**:
- Override infrastructure methods to add implicit behavior
- Handle default mapping overrides in referia's `update_name_column_map()`
- Provide convenience methods that wrap infrastructure functionality
- Make implicit behavior explicit through clear method names and documentation
- Reuse infrastructure code for non-implicit cases

**Counter-examples**:
- Expecting infrastructure to accept implicit behavior
- Making infrastructure implicit to support application needs
- Hiding implicit behavior without making it explicit
- Mixing implicit and explicit behavior in the same layer
- Not reusing infrastructure code when possible

**Conflicts**:
- **vs Code Reuse**: When handling implicit behavior requires code duplication
- Resolution: Reuse infrastructure code for non-implicit cases, only override for implicit behavior
- **vs Performance**: When explicit handling adds overhead
- Resolution: Optimize the explicit handling, don't make infrastructure implicit
