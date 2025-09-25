#!/usr/bin/env python3
"""
Run all tests for the VRChat MCP project.

This script runs all tests in the tests directory using pytest.
"""

import os
import sys
import subprocess

def run_tests():
    """Run all tests using pytest."""
    print("Running tests...")
    
    # Set the PYTHONPATH to include the src directory
    env = os.environ.copy()
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{src_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = src_dir
    
    # Run pytest
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-v', 'tests/'],
        env=env,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        check=False
    )
    
    return result.returncode

def main():
    """Main function to run tests."""
    print("VRChat MCP Test Runner")
    print("=====================")
    
    # Run tests
    return_code = run_tests()
    
    # Print summary
    print("\nTest run completed.")
    if return_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Some tests failed with exit code {return_code}")
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())
