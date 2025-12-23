---
id: "2025-12-23_conditional-widget-visibility"
title: "Conditional Widget/Template Visibility Based on Field Values"
status: "Proposed"
priority: "Medium"
created: "2025-12-23"
last_updated: "2025-12-23"
owner: ""
github_issue: ""
dependencies: ""
tags:
- backlog
- feature
- templates
- widgets
- conditional-display
- referia
---

# Task: Conditional Widget/Template Visibility Based on Field Values

## Description

Implement a mechanism to conditionally show/hide widgets or entire template instances based on field values in the data. This is needed for cases where not all sections are present in every document (e.g., not all books have all chapters).

### Use Case

In long document assessment, the `pdfpages/_referia.yml` config defines "Present" checkboxes for each chapter/section (e.g., `Ch1Present`, `Ch2Present`, etc.). When a chapter is marked as not present (checkbox unchecked), the assessment interface for that chapter should be hidden in downstream configurations like `introduction/_referia.yml`.

**Current Situation:**
```yaml
# pdfpages/_referia.yml - defines presence
output:
  columns:
    - Ch1FP
    - Ch1LP
    - Ch1Present      # ← Checkbox: is this chapter present?
    - Ch2FP
    - Ch2LP
    - Ch2Present
    # ... etc

# introduction/_referia.yml - wants to use presence
templates:
  document_chapter:
    pattern:
      - type: Markdown
        liquid: "### %title%"
      - type: Textarea
        field: "%prefix%Summary"
      # ... many more widgets

review:
  - template: document_chapter
    instances:
      - title: "Chapter 1"
        prefix: "ch1"
        # ❌ Problem: Always shows, even if Ch1Present is False
      - title: "Chapter 2"
        prefix: "ch2"
        # ❌ Problem: Always shows, even if Ch2Present is False
```

**Desired Behavior:**
- If `Ch1Present` checkbox is False, hide all widgets for Chapter 1
- If `Ch2Present` checkbox is True, show all widgets for Chapter 2
- This should work at both template level and individual widget level
- Should be reactive: checking/unchecking the checkbox updates visibility

## Acceptance Criteria

- [ ] Widgets can be conditionally displayed based on field values
- [ ] Template instances can be conditionally displayed based on field values
- [ ] Visibility updates reactively when condition field changes
- [ ] Works with boolean fields (checkboxes)
- [ ] Works with other field types (dropdowns, text comparisons)
- [ ] Clear YAML syntax for specifying conditions
- [ ] Nested templates respect visibility of parent
- [ ] Hidden widgets don't interfere with layout
- [ ] Documentation and examples provided
- [ ] Tests cover conditional display scenarios

## Proposed Syntax

### Option 1: `visible_if` Parameter

**At widget level:**
```yaml
review:
  - type: Markdown
    liquid: "### Chapter 1"
    visible_if:
      field: "Ch1Present"
      equals: true
  
  - type: Textarea
    field: "ch1Summary"
    visible_if:
      field: "Ch1Present"
      equals: true
```

**At template instance level:**
```yaml
review:
  - template: document_chapter
    instances:
      - title: "Chapter 1"
        prefix: "ch1"
    visible_if:
      field: "Ch1Present"
      equals: true
  
  - template: document_chapter
    instances:
      - title: "Chapter 2"
        prefix: "ch2"
    visible_if:
      field: "Ch2Present"
      equals: true
```

**Within template with parameter:**
```yaml
templates:
  document_chapter:
    pattern:
      - type: Markdown
        liquid: "### %title%"
        visible_if:
          field: "%prefix%Present"  # ← Uses template parameter
          equals: true
      - type: Textarea
        field: "%prefix%Summary"
        visible_if:
          field: "%prefix%Present"
          equals: true
```

### Option 2: Conditional Block Wrapper

```yaml
review:
  - type: conditional
    condition:
      field: "Ch1Present"
      equals: true
    entries:
      - type: Markdown
        liquid: "### Chapter 1"
      - type: Textarea
        field: "ch1Summary"
      # ... more widgets
```

### Option 3: Simplified Boolean Check

For simple boolean (checkbox) fields:

```yaml
review:
  - template: document_chapter
    instances:
      - title: "Chapter 1"
        prefix: "ch1"
    visible_if: "Ch1Present"  # ← Simple field name for boolean check
```

## Implementation Approaches

### Approach 1: Static Filtering (Template Expansion Time)

**When**: During template expansion in `Interface._expand_templates_in_review()`

**How**:
1. Check condition field value from inherited data
2. If condition is false, don't include the expanded widgets
3. Simple, no runtime overhead

**Pros**:
- Fast - no runtime cost
- Simple implementation
- No widget creation for hidden items

**Cons**:
- ❌ **Not reactive**: Can't change visibility after load
- ❌ Requires data to be available during config load
- ❌ Can't use for interactive scenarios

### Approach 2: Widget-Level Visibility (Creation Time)

**When**: During widget creation in `extract_widget()` or `extract_review()`

**How**:
1. Create all widgets but mark some as hidden
2. Set ipywidgets `layout.display = 'none'` for hidden widgets
3. Store condition info with widget
4. Update visibility when condition field changes

**Pros**:
- ✅ **Reactive**: Can update visibility dynamically
- ✅ Works with existing widget infrastructure
- ✅ ipywidgets native visibility support

**Cons**:
- Creates all widgets (memory overhead)
- Requires event handling for reactivity
- More complex implementation

**Implementation Details**:

```python
# In extract_widget() or extract_review()
if "visible_if" in details:
    condition = details["visible_if"]
    field_name = condition.get("field")
    expected_value = condition.get("equals", True)
    
    # Get current field value
    current_value = reviewer._data.at[reviewer._index, field_name]
    
    # Set initial visibility
    if "args" not in args:
        args["args"] = {}
    if "layout" not in args["args"]:
        args["args"]["layout"] = {}
    
    if current_value != expected_value:
        args["args"]["layout"]["display"] = "none"
    
    # Register callback for field changes
    def update_visibility(change):
        is_visible = change['new'] == expected_value
        widget.layout.display = '' if is_visible else 'none'
    
    reviewer._data.observe_field(field_name, update_visibility)
```

### Approach 3: Cluster-Level Visibility

**When**: During widget cluster creation

**How**:
1. Wrap conditional widgets in a `ConditionalWidgetCluster`
2. Cluster manages visibility of all children
3. Similar to existing `GroupWidgetCluster`, `LoadWidgetCluster`

**Pros**:
- ✅ Clean abstraction
- ✅ Matches existing cluster pattern
- ✅ Can hide entire template instances efficiently

**Cons**:
- More code to write
- New widget cluster type

## Recommended Approach

**Hybrid: Approach 2 (Widget-Level) + Approach 3 (Cluster-Level)**

1. **Template Instance Level**: Use `ConditionalWidgetCluster` to wrap entire template expansions
2. **Individual Widget Level**: Use `visible_if` parameter processed in `extract_widget()`
3. **Both are reactive**: Listen to field changes and update `layout.display`

This provides:
- ✅ Flexibility: Works at both template and widget level
- ✅ Reactivity: Updates when condition changes
- ✅ Efficiency: Can hide groups efficiently
- ✅ Clean syntax: Clear YAML configuration

## Implementation Plan

### Phase 1: Basic Widget Visibility

1. **Add `visible_if` parameter handling in `extract_widget()`**:
   - Parse condition specification
   - Get initial field value
   - Set widget `layout.display` accordingly
   - Register field observer for reactivity

2. **Support simple conditions**:
   - Equality check: `field: "Ch1Present", equals: true`
   - Boolean shorthand: `visible_if: "Ch1Present"`

3. **Tests**:
   - Widget initially hidden when condition false
   - Widget becomes visible when field changes
   - Widget becomes hidden when field changes

### Phase 2: Template-Level Visibility

1. **Add `visible_if` support at template instance level**:
   - Apply condition to all widgets in expanded template
   - Use `ConditionalWidgetCluster` wrapper

2. **Parameter substitution in conditions**:
   - Allow `%prefix%Present` in template conditions
   - Substitute during template expansion

3. **Tests**:
   - Template instance hidden when condition false
   - All widgets in template show/hide together
   - Parameter substitution works correctly

### Phase 3: Advanced Conditions

1. **Support more condition types**:
   - Not equals: `not_equals`
   - Greater/less than: `greater_than`, `less_than`
   - In list: `in: [value1, value2]`
   - Regex match: `matches: "pattern"`

2. **Logical operators**:
   - AND: `all: [condition1, condition2]`
   - OR: `any: [condition1, condition2]`
   - NOT: `not: condition`

3. **Tests**:
   - All condition types work correctly
   - Logical operators combine properly

### Phase 4: Documentation and Examples

1. **Update CIP-0009** with conditional visibility
2. **Add examples to documentation**
3. **Update `_referia.yml` templates** to use new feature
4. **Migration guide** for existing configs

## Technical Considerations

### ipywidgets Visibility

ipywidgets supports visibility via `layout.display`:

```python
# Hide widget
widget.layout.display = 'none'

# Show widget
widget.layout.display = ''  # or 'flex', 'block', etc.
```

### Data Observation

lynguine's `CustomDataFrame` should support field observation:

```python
# Check if observation exists
if hasattr(reviewer._data, 'observe_field'):
    reviewer._data.observe_field(field_name, callback)
else:
    # Alternative: observe widget directly
    field_widget = reviewer.get_widget(field_name)
    field_widget.observe(callback, names='value')
```

### Nested Templates

When template A includes template B, and both have visibility conditions:
- Inner condition should be AND'ed with outer condition
- If parent is hidden, children should also be hidden
- Implementation: Track condition chain during expansion

### Performance

For 20+ chapters with complex templates:
- Creating all widgets: ~100-200ms overhead
- Hiding via CSS: negligible runtime cost
- Field observation: minimal overhead
- **Acceptable for typical use cases**

## Alternative Designs Considered

### 1. Lazy Widget Creation

Don't create hidden widgets until needed.

**Pros**: Memory efficient
**Cons**: Complex state management, breaks existing architecture
**Decision**: Not worth complexity for typical use cases

### 2. Server-Side Filtering

Filter widgets before sending to browser.

**Pros**: Most efficient
**Cons**: Requires server architecture, major refactor
**Decision**: Out of scope

### 3. Computed Visibility Property

Define visibility as a compute function.

**Pros**: Very flexible
**Cons**: Overkill for simple boolean checks
**Decision**: Can be added later if needed

## Use Cases Beyond Thesis Assessment

1. **Grant Applications**: Show/hide sections based on grant type
2. **Job Applications**: Different fields for different positions
3. **Conditional Forms**: Show additional fields based on previous answers
4. **Multi-Level Reviews**: Show expert sections only for expert reviewers
5. **Staged Workflows**: Show different widgets at different stages

## Related Work

### Similar Features in Other Systems

- **React**: Conditional rendering with `{condition && <Component />}`
- **Vue.js**: `v-if` directive
- **Angular**: `*ngIf` structural directive
- **Jupyter Widgets**: Layout `visibility` parameter
- **HTML/CSS**: `display: none` and `visibility: hidden`

## Example: Complete Configuration

```yaml
# pdfpages/_referia.yml (inherited by introduction)
output:
  columns:
    - Ch1Present
    - Ch2Present
    - Ch3Present

# introduction/_referia.yml
templates:
  document_chapter:
    pattern:
      - type: Markdown
        liquid: "### %title%"
      - type: Textarea
        field: "%prefix%Summary"
        args:
          description: "Summary"
          rows: 10
      - type: Textarea
        field: "%prefix%Comments"
        args:
          description: "Comments"
          rows: 10

review:
  - template: document_chapter
    instances:
      - title: "Chapter 1"
        prefix: "ch1"
    visible_if: "Ch1Present"  # ← Entire template instance conditionally visible
  
  - template: document_chapter
    instances:
      - title: "Chapter 2"
        prefix: "ch2"
    visible_if: "Ch2Present"
  
  - template: document_chapter
    instances:
      - title: "Chapter 3"
        prefix: "ch3"
    visible_if: "Ch3Present"
  
  # Alternative: Use parameter substitution
  # - template: document_chapter
  #   instances:
  #     - title: "Chapter 1"
  #       prefix: "ch1"
  #   visible_if:
  #     field: "%prefix%Present"  # → becomes "ch1Present"
  #     equals: true
```

## Questions for Discussion

1. Should visibility conditions be evaluated at:
   - Config load time (static)
   - Widget creation time (semi-static)
   - Runtime (fully reactive)
   - **Recommendation**: Runtime for maximum flexibility

2. Should hidden widgets:
   - Not be created at all (lazy)
   - Be created but hidden (`display: none`)
   - **Recommendation**: Created but hidden (simpler, more reliable)

3. How should nested conditions interact:
   - AND logic (both must be true)
   - Parent overrides child
   - **Recommendation**: AND logic

4. Should there be a global "show all" debug mode:
   - Yes, for development/debugging
   - No, not needed
   - **Recommendation**: Yes, add debug flag

## Progress Updates

### 2025-12-23

- Feature proposed based on PhD thesis assessment use case
- Three implementation approaches documented
- Hybrid approach recommended (widget-level + cluster-level)
- Implementation plan defined
- Examples and syntax proposals created
- Waiting for review and approval before implementation

