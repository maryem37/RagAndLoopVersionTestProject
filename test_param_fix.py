#!/usr/bin/env python3
"""
Simple test of the parameter fix
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agents.test_writer import _step_to_annotation, _java_params

# Test case: Gherkin step with 2 string parameters
step = 'the employee submits a leave request from "future" to "past"'

# Get annotation with {string} placeholders
annotation = _step_to_annotation(step)
print(f"Step:       {step}")
print(f"Annotation: {annotation}")

# Get param list with correct arity
params = _java_params(annotation)
print(f"Params:     {params}")

# Count placeholders
string_count = annotation.count("{string}")
param_count = len(params.split(", ")) if params else 0
print(f"\nExpected {string_count} parameters")
print(f"Generated {param_count} parameters: [{params}]")

if param_count == string_count:
    print("✓ MATCH - Fix successful!")
    sys.exit(0)
else:
    print("✗ MISMATCH - Fix failed!")
    sys.exit(1)
