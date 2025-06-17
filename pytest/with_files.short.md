# File-Based Testing Requirements

## Structure
```
tests/environment/
├── sample_outputs/    # Reference files (modification prohibited)
├── result_outputs/    # Test results (overwrite OK, deletion prohibited)  
└── custom_folders/    # Additional folders as needed
```

## Rules
1. **No Isolation**: Use actual file system instead of creating/deleting temporary files
2. **Fixed Reference Points**: `sample_outputs/` serves as test baseline, modify only when module operates differently than developer intentions
3. **Persistent Results**: `result_outputs/` files remain after tests (for debugging)
4. **Partial Validation**: Verify core parts only, not complete matches
5. **Complete Validation**: Required for final target files that represent main deliverables
6. **Simplification**: Cover multiple tests with one or few files, core functionality over coverage

## Verification Approach
- **Structural verification** for JSON/YAML key existence and types
- **Partial comparison** using essential keywords, not entire lines
- **Pattern-based verification** only when absolutely necessary (regex hard to understand)
- **Complete comparison** for final output files that developers expect as end goals

## Purpose
- Visual confirmation of test results
- Easy debugging when failures occur  
- Prevent excessive test complexity
- Helper functions need only work well for intended purpose, not all inputs

Write pytest using this approach.
