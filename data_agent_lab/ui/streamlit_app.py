"""Streamlit workbench for Data-Agent-Lab."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from data_agent_lab.agents.pipeline import analyze


def main() -> None:
    st.set_page_config(page_title="Data-Agent-Lab", layout="wide")
    st.title("Data-Agent-Lab Workbench")
    st.caption("Verification-native data analysis agent")

    data_path = st.text_input("Data path (CSV file or folder)", value="examples/csv_revenue/data")
    question = st.text_area("Question", value="What was Electronics revenue in 2024-02?")

    if st.button("Run analysis", type="primary"):
        path = Path(data_path)
        if not path.exists():
            st.error(f"Path not found: {path}")
            return
        with st.spinner("Running pipeline..."):
            result = analyze(question, path)
        st.success(f"Status: {result.status} · Run `{result.run_id}`")
        st.subheader("Answer")
        st.write(result.answer)
        st.subheader("Validation")
        log_path = result.run_root / "validation" / "validation_log.json"
        if log_path.exists():
            st.json(log_path.read_text(encoding="utf-8"))
        report_path = result.run_root / "report" / "report.md"
        if report_path.exists():
            st.subheader("Report")
            st.markdown(report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
