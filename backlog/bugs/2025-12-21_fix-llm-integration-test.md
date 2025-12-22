---
id: "2025-12-21_fix-llm-integration-test"
title: "Fix failing LLM summarise function test"
status: "Proposed"
priority: "Low"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: "lawrennd"
github_issue: null
dependencies: null
tags:
- backlog
- bugs
- testing
- llm
- integration
---

# Bug: Fix failing LLM summarise function test

## Description

One test in `referia/tests/test_llm_integration.py` is failing. This failure is **pre-existing** and not related to CIP-0005 implementation. It was discovered during Phase 2 regression testing.

The test relates to LLM integration for summarisation functionality.

## Failing Test

`test_llm_integration.py::TestLLMComputeFunctions::test_llm_summarise_function`

**Error:**
```
ValueError: A user_file must be provided when initialising an Interface object.
```

**Location:** `/Users/neil/lawrennd/lynguine/lynguine/config/interface.py:325`

## Root Cause Analysis

The error indicates the test is trying to create an Interface object without providing a `user_file` parameter, which is now required.

**Possible causes:**
1. Test setup incomplete - missing required configuration file
2. API change in Interface class made `user_file` required
3. Test needs updating to match current Interface API

## Impact

- **Test Suite**: 1/225 tests failing (0.4% failure rate)
- **Functionality**: LLM summarise feature may or may not work (test might be outdated)
- **User Impact**: Unknown - depends on whether feature itself works
- **Severity**: Low - single integration test, functionality may still work

## Discovery Context

Found during CIP-0005 Phase 2 regression testing on 2025-12-21. This is **not caused by CIP-0005** - it's a pre-existing failure in LLM integration tests.

## Acceptance Criteria

- [ ] Test `test_llm_summarise_function` passes
- [ ] Test properly initializes Interface object with required parameters
- [ ] LLM summarise functionality verified to work
- [ ] No regressions in other LLM integration tests

## Investigation Notes

### Hypothesis 1: Test needs Interface configuration file
The test might need to create a temporary `_referia.yml` file or pass `user_file` parameter when creating the Interface.

### Hypothesis 2: API changed but test not updated
The Interface class might have changed its API to require `user_file`, but the test wasn't updated accordingly.

### Files to Examine

- `referia/tests/test_llm_integration.py` - Failing test
- `lynguine/config/interface.py:325` - Where error is raised
- Other LLM integration tests that pass - see how they initialize Interface

## Related

- Discovered during: CIP-0005 Phase 2 regression testing
- Not related to: CIP-0005 mapping timing implementation
- Related file: `lynguine/config/interface.py`

## Progress Updates

### 2025-12-21

Bug identified during CIP-0005 Phase 2 regression testing. Confirmed as pre-existing (not caused by CIP-0005). Created backlog item to track the issue for future resolution.

Priority set to Low because:
- Single test failure
- Integration test (not core functionality)
- Unclear if actual feature is broken or just test


