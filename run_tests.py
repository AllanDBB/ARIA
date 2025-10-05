"""
ARIA SDK Test Runner
====================

Convenient script to run all tests with various options.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --fast       # Run with minimal output
    python run_tests.py --coverage   # Run with coverage report
    python run_tests.py --html       # Generate HTML report
    python run_tests.py --parallel   # Run tests in parallel
    python run_tests.py --module codec  # Run specific module tests
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(args):
    """
    Run tests with specified options.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    # Build pytest command
    cmd = ['pytest', 'test/']
    
    # Add verbosity
    if not args.fast:
        cmd.append('-v')
    
    # Add coverage
    if args.coverage:
        cmd.extend(['--cov=aria_sdk', '--cov-report=term-missing'])
        if args.html:
            cmd.append('--cov-report=html')
    
    # Add HTML report
    if args.html and not args.coverage:
        cmd.extend(['--html=test_report.html', '--self-contained-html'])
    
    # Add parallel execution
    if args.parallel:
        cmd.extend(['-n', 'auto'])
    
    # Filter by module
    if args.module:
        cmd[1] = f'test/test_{args.module}.py'
    
    # Add markers
    if args.markers:
        cmd.extend(['-m', args.markers])
    
    # Add keyword filter
    if args.keyword:
        cmd.extend(['-k', args.keyword])
    
    # Show output
    if args.show_output:
        cmd.append('-s')
    
    # Stop on first failure
    if args.failfast:
        cmd.append('-x')
    
    # Rerun failed tests
    if args.lf:
        cmd.append('--lf')
    
    # Print command
    print(f"🚀 Running: {' '.join(cmd)}")
    print("=" * 70)
    
    # Run tests
    result = subprocess.run(cmd)
    
    # Print summary
    print("\n" + "=" * 70)
    if result.returncode == 0:
        print("✅ All tests passed!")
        if args.coverage:
            print("📊 Coverage report generated")
            if args.html:
                print("   Open htmlcov/index.html to view")
    else:
        print("❌ Some tests failed")
        print("   Run with --lf to rerun only failed tests")
    
    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ARIA SDK Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --coverage --html  # With coverage and HTML report
  python run_tests.py --parallel         # Run in parallel (faster)
  python run_tests.py --module codec     # Run only codec tests
  python run_tests.py --keyword compress # Run tests matching 'compress'
  python run_tests.py --lf               # Rerun last failed tests
        """
    )
    
    # Test selection
    parser.add_argument(
        '--module',
        choices=['entities', 'codec', 'compression', 'storage', 'streaming', 'integration'],
        help='Run tests for specific module only'
    )
    parser.add_argument(
        '--keyword', '-k',
        help='Run tests matching keyword expression'
    )
    parser.add_argument(
        '--markers', '-m',
        help='Run tests with specific markers'
    )
    
    # Output options
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Run with minimal output (no -v flag)'
    )
    parser.add_argument(
        '--show-output', '-s',
        action='store_true',
        help='Show print statements and output'
    )
    
    # Reports
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML report (requires --coverage or standalone)'
    )
    
    # Execution options
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run tests in parallel (requires pytest-xdist)'
    )
    parser.add_argument(
        '--failfast', '-x',
        action='store_true',
        help='Stop on first test failure'
    )
    parser.add_argument(
        '--lf',
        action='store_true',
        help='Rerun only tests that failed last time'
    )
    
    args = parser.parse_args()
    
    # Validate
    test_dir = Path('test')
    if not test_dir.exists():
        print("❌ Error: test/ directory not found")
        print("   Make sure you're in the project root directory")
        return 1
    
    # Run tests
    return run_tests(args)


if __name__ == '__main__':
    sys.exit(main())
