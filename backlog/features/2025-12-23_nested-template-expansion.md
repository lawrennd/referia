---
id: "2025-12-23_nested-template-expansion"
title: "Add Recursive/Nested Template Expansion Support"
status: "Completed"
priority: "Medium"
created: "2025-12-23"
last_updated: "2025-12-23"
owner: ""
github_issue: ""
dependencies: ""
tags:
- backlog
- feature
- template-expansion
- cip-0006
---

# Task: Add Recursive/Nested Template Expansion Support

## Description

Enhance the CIP-0006 template expansion system to support nested templates, where a template's `pattern` can reference other templates. This would enable composition of complex interfaces from smaller, reusable template pieces.

Currently, `_expand_templates_in_review()` does a single pass through the review section. Once a template is expanded, the resulting entries are not checked again for template references. This means if a template's `pattern` contains another `template` reference, it would be passed through unexpanded.

## Use Cases

1. **Template Composition**: Create a "comment_section" template that can be nested within multiple other templates like "chapter_review", "abstract_review", etc.

2. **DRY Principle**: Define common widget patterns once and reuse them across multiple higher-level templates.

3. **Hierarchical Structure**: Build complex review interfaces from smaller, well-defined building blocks.

Example:
```yaml
templates:
  # Base template for comment collection
  comment_section:
    pattern:
      - type: Textarea
        field: "%prefix%Comments"
      - type: PopulateButton
        target: "%prefix%Comments"
        
  # Higher-level template that uses comment_section
  chapter_review:
    pattern:
      - type: Markdown
        liquid: "### %title%"
      - template: comment_section
        instances:
          - prefix: "%prefix%General"
      - template: comment_section
        instances:
          - prefix: "%prefix%Technical"
```

## Acceptance Criteria

- [x] Template patterns can reference other templates using `template` key
- [x] Parameters are correctly passed through nested levels
- [x] Recursive expansion continues until no more template references exist
- [x] Circular references are detected and raise clear error
- [x] Maximum recursion depth is configurable (default: 10 to prevent infinite loops)
- [x] All existing tests continue to pass
- [x] New tests cover nested template scenarios

## Implementation Notes

Two possible approaches:

### Option 1: Recursive Function
Modify `_expand_templates_in_review()` to recursively process expanded entries:

```python
def _expand_templates_in_review(self, review, depth=0, max_depth=10):
    if depth > max_depth:
        raise ValueError(f"Maximum template nesting depth ({max_depth}) exceeded")
    
    expanded_review = []
    has_templates = False
    
    for entry in review:
        if isinstance(entry, dict) and 'template' in entry:
            has_templates = True
            # Expand template...
            expanded_entries = self._expand_template_instance(...)
            # Recursively check expanded entries for more templates
            nested_expanded = self._expand_templates_in_review(
                expanded_entries, depth + 1, max_depth
            )
            expanded_review.extend(nested_expanded)
        else:
            expanded_review.append(entry)
    
    return expanded_review
```

### Option 2: Multi-Pass
Keep doing passes until no more template references are found:

```python
def _expand_templates_in_review(self, review):
    max_iterations = 10
    current = review
    
    for iteration in range(max_iterations):
        expanded = self._single_pass_expansion(current)
        if self._has_template_references(expanded):
            current = expanded
        else:
            return expanded
    
    raise ValueError("Maximum template expansion iterations exceeded")
```

**Recommended**: Option 1 (recursive) is cleaner and provides better error context with depth tracking.

### Additional Considerations

1. **Circular Reference Detection**: Track the chain of template names during expansion and detect cycles.

2. **Parameter Inheritance**: Decide whether nested templates inherit parameters from parent or need explicit passing.

3. **Error Messages**: Provide clear stack trace showing template expansion chain when errors occur.

4. **Performance**: Ensure deep nesting doesn't significantly impact configuration load time.

## Related

- CIP: 0006 (Template Expansion System)
- Related backlog: 2025-12-23_template-expansion-column-generation (completed)
- Current implementation: `referia/config/interface.py::_expand_templates_in_review()`

## Progress Updates

### 2025-12-23

- Feature proposed after user inquiry about template nesting capability
- Current implementation does single-pass expansion only
- Use cases and implementation approaches documented
- **Implementation completed:**
  - Implemented recursive `_expand_templates_in_review()` with depth tracking
  - Added circular reference detection with clear error messages
  - Added maximum depth limit (default: 10) to prevent infinite loops
  - Added 5 comprehensive tests covering:
    - Single-level nesting
    - Multiple-level nesting (3 levels deep)
    - Circular reference detection
    - Maximum depth exceeded detection
    - Multiple instances at nested levels
  - All 16 template expansion tests pass
  - Feature fully functional and tested

