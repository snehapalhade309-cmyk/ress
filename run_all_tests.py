"""
ResQAI - Automated Test Suite Runner
Runs unit and integration tests and prints an honest, structured verification summary.
"""

import os
import sys
import unittest
import time

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_tests():
    print("=" * 70)
    print(" RESQAI - AUTOMATED TEST SUITE & VERIFICATION RUNNER")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover and add test modules from tests directory
    tests_dir = os.path.join(PROJECT_ROOT, 'tests')
    discovered = loader.discover(tests_dir, pattern='test_*.py')
    suite.addTests(discovered)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start_time

    total = result.testsRun
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failed - errors - skipped

    print("\n" + "=" * 70)
    print(" TEST EXECUTION SUMMARY")
    print("=" * 70)
    print(f" Total Tests Run : {total}")
    print(f" Passed          : {passed} ({(passed/total*100):.1f}%)" if total > 0 else 0)
    print(f" Failed          : {failed}")
    print(f" Errors          : {errors}")
    print(f" Skipped/Untested: {skipped}")
    print(f" Total Duration  : {duration:.2f} seconds")
    print("=" * 70)

    if failed > 0 or errors > 0:
        print("[FAIL] STATUS: TESTS FAILED. Review errors above.")
        sys.exit(1)
    else:
        print("[PASS] STATUS: ALL TEST CHECKS PASSED SUCCESSFULLY.")
        sys.exit(0)


if __name__ == '__main__':
    run_tests()
