# File-Based Testing Guide (Detailed Version)

## Overview

Instead of traditional isolated testing approaches, we use a file system-based testing methodology. This allows direct verification of test results, facilitates easier debugging, and reduces testing complexity.

## Basic Directory Structure

```
tests/
└── environment/
    ├── sample_outputs/     # Reference files (modification prohibited)
    └── result_outputs/     # Test execution result files (overwrite allowed)
```

Additional folders can be created as needed:
```
tests/
└── environment/
    ├── sample_outputs/     # Reference files (modification prohibited)
    ├── result_outputs/     # Test execution result files (overwrite allowed)
    ├── custom_folder1/
    └── custom_folder2/
```

## Core Principles

### 1. No Isolation
- Do not create and delete temporary files within tests
- Prohibit use of `tempfile`, `tmp_path`, and other temporary directory utilities
- Use fixed paths in the actual file system

### 2. Fixed Reference Points
- Files in `sample_outputs/` serve as reference points for developers to understand module operation
- These files are modified when the module is determined to be operating differently than developer intentions
- Never modify these files without developer consent just to force failing tests to pass

### 3. Persistent Results
- Files in `result_outputs/` are maintained even after test execution
- Files with the same name can be overwritten
- When tests fail, developers can directly open and examine the files

### 4. Partial Validation
- Complete file matching is not required
- Verify only core functionality-related portions
- Exclude dynamic values like timestamps, UUIDs from verification

### 5. Simplicity First
- Cover multiple test cases with one or a few files
- Focus on core functionality rather than overly granular tests, even if coverage is somewhat lower
- Too many tests can actually hinder maintenance
- Helper functions especially need only to perform their intended purpose well, not work perfectly for all inputs

## Test Writing Process

### 1. Setup Phase
- Verify that necessary input files are prepared under the environment directory
- Check if result output directory exists (create if absent)
- Validate that dependencies required for testing are ready

### 2. Execute Phase
- Execute the actual functionality to be tested
- Read and process input files
- Save results as files in the `result_outputs/` directory

### 3. Verify Phase
- Confirm that result files were generated
- Compare with reference files in `sample_outputs/`
- **Partial verification**: Verify only core portions, not the entirety
- Exclude dynamic values (timestamps, UUIDs, etc.) from verification

### 4. No Cleanup
- Do not delete generated files
- Maintain files so developers can directly examine them when tests fail

## Verification Strategy Methods

### Complete Comparison
- Use for very simple cases where output is completely predictable
- **Use for final target files that developers expect as end goals**
- When the entire output represents the core deliverable of the functionality
- Examples: final configuration files, complete template rendering results, generated code files
- Essential for validating that the main purpose of the module is achieved correctly

### Pattern-Based Verification
- Regular expression-based tests are difficult for developers to understand at a glance
- Use only when absolutely necessary

### Structural Verification
- For structural data like JSON, YAML
- Check existence of required keys, data types
- Verify correct hierarchical structure

### Partial Comparison
- Compare only specific sections or lines of files
- Confirm that important parts are generated as expected
- Ignore other parts (e.g., comments, metadata)
- Requiring entire lines verbatim is also prohibited
- Verify essential keywords separately and expand as needed

## Advantages

1. **Transparency**: Direct visual confirmation of test results possible
2. **Debugging Ease**: Direct analysis of generated files when failures occur
3. **Enhanced Understanding**: Understand functionality by seeing actual input/output
4. **Maintainability**: No excessive mocking or isolation code
5. **Realism**: Testing similar to actual usage environment