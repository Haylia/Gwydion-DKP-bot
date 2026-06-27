"""Run every unit-test suite for the bot. Usage:  python run_tests.py

Each test module exposes a `_TESTS` list of zero-arg functions that assert and
print an `ok:` line. None of them need Discord, gspread, or credentials — they run
against the bot source via the `test_support` harness. Exits non-zero on any
failure (suitable for CI). Pytest also works: `pytest` discovers the `test_*`
functions directly.
"""
import importlib
import traceback

MODULES = ["test_helpers", "test_bid_store", "test_state"]


def main():
    total = passed = 0
    failures = []
    for modname in MODULES:
        mod = importlib.import_module(modname)
        print(f"\n=== {modname} ===")
        for t in getattr(mod, "_TESTS", []):
            total += 1
            try:
                t()
                passed += 1
            except Exception:
                failures.append(f"{modname}.{t.__name__}")
                print(f"FAIL: {t.__name__}")
                traceback.print_exc()
    print(f"\n{passed}/{total} tests passed")
    if failures:
        print("FAILURES: " + ", ".join(failures))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
