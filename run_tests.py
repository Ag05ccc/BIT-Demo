#!/usr/bin/env python3
"""
Test runner for Product Test BIT application.
Run all tests locally to verify code architecture and flow.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose output
    python run_tests.py -k models    # Run only model tests
    python run_tests.py --cov        # With coverage report
"""

import sys
import os

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(__file__)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'server'))

if __name__ == '__main__':
    import pytest

    args = [
        'tests/',
        '-v',
        '--tb=short',
        '--no-header',
    ]

    # Pass through any command line arguments
    args.extend(sys.argv[1:])

    exit_code = pytest.main(args)
    sys.exit(exit_code)
