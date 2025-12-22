---
id: "2025-12-22_reorganize-test-suite-structure"
title: "Reorganise Test Suite Structure and Naming Conventions"
status: "Proposed"
priority: "Low"
created: "2025-12-22"
last_updated: "2025-12-22"
owner: "lawrennd"
github_issue: null
dependencies: null
tags:
- backlog
- infrastructure
- testing
- organization
- refactoring
---

# Task: Reorganise Test Suite Structure and Naming Conventions

## Description

The referia test suite has grown organically and now has inconsistent structure, naming conventions, and organization. This makes it difficult to navigate, understand test coverage, and maintain the test suite. A systematic reorganization would improve developer experience and test maintainability.

## Motivation

### Current Issues

**1. Inconsistent Test Locations**:
```
referia/tests/           # Some tests here
tests/                   # Other tests here
referia/referia/tests/   # Not currently used but exists
```

**2. Inconsistent Naming Conventions**:
```
tests/test_template_loading.py         # test_ prefix
tests/test_parameter_substitution.py   # test_ prefix
tests/test_template_integration.py     # test_ prefix
tests/test_template_regression.py      # test_ prefix
tests/test_global_consts.py            # test_ prefix
tests/test_from_flow_mapping_timing.py # test_ prefix
tests/test_implicit_mapping_behavior.py # test_ prefix
tests/test_claude.py                   # Unclear purpose
```

**3. Lack of Clear Organization**:
- No separation by component (config, assess, access, etc.)
- No separation by test type (unit, integration, regression)
- Template tests split across 4 files (could be organized better)
- Unclear which tests are for referia vs lynguine features

**4. Mixed Test Purposes**:
- Unit tests mixed with integration tests
- Feature tests mixed with regression tests
- Bug reproduction tests mixed with feature tests

## Acceptance Criteria

- [ ] Consistent test directory structure
- [ ] Clear naming conventions documented and followed
- [ ] Tests organized by component and type
- [ ] Easy to find tests for specific functionality
- [ ] Test organization documented in TESTING.md or similar
- [ ] All tests still pass after reorganization
- [ ] CI/CD updated if test paths change

## Proposed Structure

### Option 1: By Component and Type

```
tests/
├── README.md                      # Testing guide
├── conftest.py                    # Shared fixtures
├── unit/                          # Fast, isolated tests
│   ├── config/
│   │   ├── test_interface.py
│   │   ├── test_template_loading.py
│   │   └── test_parameter_substitution.py
│   ├── assess/
│   │   └── test_data.py
│   └── access/
│       └── test_access.py
├── integration/                   # Tests crossing components
│   ├── test_template_expansion.py
│   ├── test_global_consts_integration.py
│   └── test_mapping_behavior.py
├── regression/                    # Bug prevention & real-world scenarios
│   ├── test_template_patterns.py
│   ├── test_cip0005_regression.py
│   └── test_write_modes.py
└── fixtures/                      # Shared test data
    ├── sample_configs/
    ├── sample_data/
    └── templates/
```

### Option 2: Flat with Clear Naming

```
tests/
├── README.md
├── conftest.py
├── unit_config_interface.py
├── unit_config_template_loading.py
├── unit_config_template_substitution.py
├── integration_template_expansion.py
├── integration_global_consts.py
├── regression_template_patterns.py
├── regression_cip0005.py
└── fixtures/
```

### Option 3: By Feature

```
tests/
├── README.md
├── conftest.py
├── template_expansion/          # All template-related tests
│   ├── test_loading.py
│   ├── test_substitution.py
│   ├── test_integration.py
│   └── test_regression.py
├── global_consts/              # All global_consts tests
│   ├── test_loading.py
│   └── test_integration.py
├── mapping/                    # All mapping tests
│   ├── test_behavior.py
│   └── test_timing.py
└── fixtures/
```

## Naming Conventions

### Test File Names

**Recommended**: `test_{component}_{feature}_{type}.py`

Examples:
- `test_config_interface_unit.py`
- `test_template_expansion_integration.py`
- `test_thesis_patterns_regression.py`

Or with flat structure:
- `unit_config_interface.py`
- `integration_template_expansion.py`
- `regression_thesis_patterns.py`

### Test Class Names

```python
# Current (inconsistent)
class TestInlineTemplateLoading:      # Good
class TestGlobalConstsBasicLoading:   # Good
class TestComplexScenarios:           # Too vague

# Proposed (consistent)
class TestTemplateLoadingInline:      # Component_Feature_Detail
class TestGlobalConstsLoading:        # Component_Feature
class TestThesisReviewPatterns:       # Feature_Context
```

### Test Function Names

```python
# Current (inconsistent)
def test_load_single_inline_template():           # Good - descriptive
def test_simple_field_substitution():             # Good - descriptive
def test_expanded_config_passes_to_lynguine():    # Good - descriptive
def test_thesis_review_pattern():                 # Could be more specific

# Proposed (consistent pattern)
def test_{what}_{condition}_{expected}():

# Examples:
def test_template_loading_single_inline_succeeds():
def test_parameter_substitution_missing_param_raises():
def test_config_expansion_with_lynguine_succeeds():
def test_thesis_pattern_12_chapters_creates_36_widgets():
```

## Implementation Notes

### Migration Strategy

1. **Phase 1: Document Current State**
   - Inventory all test files
   - Categorize by component, type, purpose
   - Identify duplicates or gaps

2. **Phase 2: Design New Structure**
   - Choose one of the proposed options (or hybrid)
   - Document naming conventions
   - Get team approval

3. **Phase 3: Migrate Gradually**
   - Create new structure (empty)
   - Move tests one component at a time
   - Update imports and fixtures
   - Verify all tests pass after each move

4. **Phase 4: Update CI/CD**
   - Update test discovery paths
   - Update coverage reporting
   - Update documentation

5. **Phase 5: Document**
   - Create TESTING.md guide
   - Document structure and conventions
   - Include examples for new tests

### Migration Order (Suggested)

1. **Template tests** (4 files) - Most recent, fresh in mind
2. **Global consts tests** - Recently organized
3. **Mapping tests** - Well-defined scope
4. **Legacy tests** - Understand and categorize

### Backward Compatibility

- Keep old test paths working temporarily (symlinks or duplicates)
- Update gradually over multiple PRs
- Document migration in commits

## Testing Strategy

### Before Migration
- [ ] Run full test suite, capture results
- [ ] Document test execution time
- [ ] Note any flaky tests

### During Migration
- [ ] Tests pass after each file move
- [ ] No test coverage loss
- [ ] Imports resolve correctly

### After Migration
- [ ] All tests pass
- [ ] Test execution time similar or better
- [ ] Coverage reports work correctly
- [ ] CI/CD updated and working

## Estimated Effort

- **Phase 1** (Document): 2-3 hours
- **Phase 2** (Design): 2-3 hours
- **Phase 3** (Migrate): 1-2 days (depending on test count)
- **Phase 4** (CI/CD): 2-4 hours
- **Phase 5** (Document): 2-3 hours

**Total**: 2-3 days

## Benefits

### Developer Experience
- Easier to find relevant tests
- Clear where to add new tests
- Understand test organization at a glance
- Consistent patterns across codebase

### Maintainability
- Reduce confusion about test locations
- Easier to identify coverage gaps
- Simpler to refactor or reorganize
- Better separation of concerns

### CI/CD
- Can run test subsets (unit only, integration only)
- Faster feedback loops (run fast tests first)
- Clearer test reports
- Better parallelization options

### Onboarding
- New contributors can navigate easily
- Clear patterns to follow
- Self-documenting structure

## Related

- **Related**: Template expansion tests (test_template_*.py) created during CIP-0006
- **Related**: Global consts tests created during bug investigation
- **Similar**: lynguine test organization (could align structures)

## Progress Updates

### 2025-12-22
Task created with Proposed status. Identified need while completing CIP-0006 template expansion feature, which added 4 new test files and highlighted the lack of consistent test organization.

**Note**: This is a cleanup task, not urgent. Could be done incrementally when touching test files for other reasons.

