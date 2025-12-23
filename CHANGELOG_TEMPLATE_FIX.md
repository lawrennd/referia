# Template Expansion and Column Generation Fix

## Date
2025-12-23

## Summary
Fixed critical bugs in CIP-0006 template expansion system that prevented proper column auto-generation and caused namespace clashes between template parameters, Liquid syntax, and display variables.

## Problems Fixed

### 1. Missing Output Columns from Template-Expanded Fields
**Symptom**: `ValueError: DataFrame contains column "abstractGeneralComments_modified" which is not in the columns list of the specification and strict_columns is set to "True"`

**Root Cause**: The auto-generation logic for `_modified` and `_created` timestamp columns only appended to an existing `columns` list in the `output` section. When the `columns` list was removed (to enable full auto-generation from templates), the code failed to create the list, resulting in missing column declarations.

**Fix**: Modified `referia/config/interface.py` to check if `data[output_type]["columns"]` exists before attempting to add timestamp columns. If missing, it now initializes the list with all fields extracted from the expanded `review` section.

```python
# In Interface.__init__ method
for output_type in output_types:
    if output_type in data:
        if "columns" not in data[output_type]:
            # Create columns list from review fields if missing
            data[output_type]["columns"] = []
            for col in review_columns:
                data[output_type]["columns"].append(col)
        
        # Now add _modified and _created columns
        if "columns" in data[output_type]:
            for column in data[output_type]["columns"]:
                # ... existing timestamp column logic ...
```

### 2. Namespace Clash Between Template Parameters and Liquid Syntax
**Symptom**: Markdown headings displaying incorrectly, with all headings showing the thesis title instead of section-specific titles. Template parameters like `{{title}}` being confused with Liquid syntax.

**Root Cause**: The template expansion system was using `{{param}}` syntax for template parameters, which collided with Liquid's `{{field}}` syntax for data binding. This caused the template substitution to incorrectly process Liquid templates, and also created confusion with display variables `{Name}`.

**Fix**: Changed template parameter syntax from `{{param}}` to `%param%` throughout:
- Updated `_substitute_parameters()` in `referia/config/interface.py` to use regex `%(\w+)%`
- Added support for escaping literal `%` signs via `%%param%%` → `%param%`
- Updated all template definitions in configuration files to use `%param%` syntax

This provides clear separation:
- `%param%` - Template expansion parameters (processed during config load)
- `{{field}}` - Liquid data binding (processed during Markdown rendering)
- `{Name}` - Display variables (processed during UI display)

## Files Modified

### Core Library
- `referia/config/interface.py`:
  - Added column list initialization logic
  - Updated `_substitute_parameters()` to use `%param%` regex
  - Added `%%param%%` escape sequence handling

### Configuration Files
- `referia/theses/examined/introduction/_referia.yml`:
  - Changed all template parameters from `{{param}}` to `%param%`
  - Changed all template parameters from `{param}` to `%param%`
  - Removed explicit `columns` list in `output` section to enable auto-generation

### Tests
- `tests/test_template_expansion.py` (NEW):
  - Tests for `%param%` substitution
  - Tests for Liquid `{{field}}` preservation
  - Tests for display `{Name}` substitution
  - Tests for auto-column generation from templates
  - Tests for `_modified`/`_created` timestamp column generation
  - Tests for error handling with missing parameters

## Testing
All 9 new tests pass:
```bash
pytest tests/test_template_expansion.py -v
# 9 passed in 8.63s
```

## Impact
- ✅ Template-expanded fields now correctly generate output columns
- ✅ Timestamp columns (`_modified`, `_created`) auto-added for all fields
- ✅ Clear separation between three templating systems
- ✅ Markdown section titles now render correctly
- ✅ No more confusion between parameter substitution and Liquid syntax
- ✅ Comprehensive test coverage prevents regression

## Related
- CIP-0006: Template Expansion System
- Issue: Button labels showing `Populate {toc}Button` instead of proper descriptions (fixed separately by adding explicit `description` fields)

