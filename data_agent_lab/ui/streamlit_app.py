"""Streamlit workbench for Data-Agent-Lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # Streamlit is an optional UI dependency.
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - exercised only without ui extra
    st = None

import pandas as pd

from data_agent_lab.agents.pipeline import AnalyzeResult, analyze
from data_agent_lab.config import RUNS_DIR


EXAMPLE_DATASETS = {
    "Revenue aggregation": Path("examples/csv_revenue/data"),
    "Multi-table join": Path("examples/multi_table"),
    "S4 monthly anomaly": Path("tests/golden/monthly_anomaly/data"),
    "S4 regression": Path("tests/golden/linear_regression_drivers/data"),
    "S4 dirty join": Path("tests/golden/dirty_join_normalized/data"),
}

EXAMPLE_QUESTIONS = {
    "Revenue aggregation": "What was Electronics revenue in 2024-02?",
    "Multi-table join": "What is total order amount by customer name?",
    "S4 monthly anomaly": "Find abnormal revenue changes by month.",
    "S4 regression": "Run regression and explain key drivers of sales.",
    "S4 dirty join": "What is total order amount by customer name?",
}


def validation_summary(validation_log: dict[str, Any]) -> dict[str, Any]:
    checks = validation_log.get("checks", [])
    failed = [c for c in checks if not c.get("passed")]
    return {
        "worst_severity": validation_log.get("worst_severity"),
        "passed": validation_log.get("passed"),
        "total_checks": len(checks),
        "failed_checks": len(failed),
        "warnings": sum(1 for c in failed if c.get("severity") == "warning"),
        "critical": sum(1 for c in failed if c.get("severity") == "critical"),
    }


def save_uploaded_csvs(uploaded_files: list[Any], base_dir: Path = RUNS_DIR) -> Path:
    upload_dir = base_dir / "streamlit_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"upload_{len(list(upload_dir.glob('upload_*'))) + 1:04d}"
    target.mkdir(parents=True, exist_ok=True)
    for file in uploaded_files:
        safe_name = Path(file.name).name
        (target / safe_name).write_bytes(file.getvalue())
    return target


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def render_artifacts(result: AnalyzeResult) -> None:
    validation_path = result.run_root / "validation" / "validation_log.json"
    report_path = result.run_root / "report" / "report.md"
    sql_path = result.run_root / "code" / "queries.sql"
    result_csv = result.run_root / "outputs" / "result.csv"

    validation_log = load_json(validation_path)
    if validation_log:
        st.subheader("Validation")
        summary = validation_summary(validation_log)
        cols = st.columns(5)
        cols[0].metric("Worst", str(summary["worst_severity"]))
        cols[1].metric("Checks", summary["total_checks"])
        cols[2].metric("Failed", summary["failed_checks"])
        cols[3].metric("Warnings", summary["warnings"])
        cols[4].metric("Critical", summary["critical"])
        with st.expander("Validation log", expanded=summary["failed_checks"] > 0):
            st.json(validation_log)

    if result_csv.exists():
        st.subheader("Result")
        st.dataframe(pd.read_csv(result_csv), use_container_width=True)

    if sql_path.exists():
        st.subheader("Generated SQL / Execution Plan")
        st.code(sql_path.read_text(encoding="utf-8"), language="sql")

    if report_path.exists():
        st.subheader("Report")
        st.markdown(report_path.read_text(encoding="utf-8"))

    st.subheader("Artifacts")
    st.code(str(result.run_root))


def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit is not installed. Install with `pip install -e '.[ui]'`.")

    st.set_page_config(page_title="Data-Agent-Lab", layout="wide")
    st.title("Data-Agent-Lab Workbench")

    with st.sidebar:
        st.header("Data")
        source_mode = st.radio("Source", ["Example", "Local path", "Upload CSV"], horizontal=False)
        data_path: Path | None = None

        if source_mode == "Example":
            selected = st.selectbox("Dataset", list(EXAMPLE_DATASETS))
            data_path = EXAMPLE_DATASETS[selected]
            default_question = EXAMPLE_QUESTIONS[selected]
            st.caption(str(data_path))
        elif source_mode == "Local path":
            data_path = Path(st.text_input("Data path", value="examples/csv_revenue/data"))
            default_question = "What was Electronics revenue in 2024-02?"
        else:
            uploaded = st.file_uploader("CSV files", type=["csv"], accept_multiple_files=True)
            default_question = "What is the total revenue?"
            if uploaded:
                data_path = save_uploaded_csvs(uploaded)
                st.caption(f"Saved upload to {data_path}")

        runs_dir = Path(st.text_input("Runs dir", value=str(RUNS_DIR)))

    question = st.text_area("Question", value=default_question, height=90)

    if st.button("Run analysis", type="primary", disabled=data_path is None):
        if data_path is None or not data_path.exists():
            st.error(f"Path not found: {data_path}")
            return
        with st.spinner("Running verified analysis..."):
            result = analyze(question, data_path, runs_dir=runs_dir)
        if result.status == "completed":
            st.success(f"Completed · `{result.run_id}`")
        else:
            st.error(f"{result.status} · `{result.run_id}`")
        st.subheader("Answer")
        st.write(result.answer)
        render_artifacts(result)


if __name__ == "__main__":
    main()
