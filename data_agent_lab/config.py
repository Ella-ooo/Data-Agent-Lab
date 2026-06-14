from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_TASKS_DIR = PROJECT_ROOT / "tests" / "golden"
RUNS_DIR = PROJECT_ROOT / "runs"
DEFAULT_BENCH_OUTPUT_DIR = RUNS_DIR / "benchmarks"
