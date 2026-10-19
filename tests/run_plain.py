"""Run tests without pytest: python tests/run_plain.py (with pytest just use `pytest`)."""
import importlib, inspect, pathlib, sys, traceback
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
failed = total = 0
for f in sorted((root / "tests").glob("test_*.py")):
    mod = importlib.import_module(f"tests.{f.stem}")
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("test_") and fn.__module__ == mod.__name__:
            total += 1
            try:
                fn()
            except Exception:
                failed += 1
                print("FAIL", f.stem, name)
                traceback.print_exc(limit=4)
print(f"{total} tests, {failed} failed")
sys.exit(1 if failed else 0)
