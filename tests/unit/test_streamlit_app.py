from data_agent_lab.ui.streamlit_app import save_uploaded_csvs, validation_summary


class Upload:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def test_validation_summary_counts_failed_checks():
    summary = validation_summary(
        {
            "worst_severity": "critical",
            "passed": False,
            "checks": [
                {"name": "a", "passed": True, "severity": "info"},
                {"name": "b", "passed": False, "severity": "warning"},
                {"name": "c", "passed": False, "severity": "critical"},
            ],
        }
    )

    assert summary["total_checks"] == 3
    assert summary["failed_checks"] == 2
    assert summary["warnings"] == 1
    assert summary["critical"] == 1


def test_save_uploaded_csvs_writes_files(tmp_path):
    target = save_uploaded_csvs(
        [Upload("../unsafe.csv", b"x\n1\n"), Upload("safe.csv", b"y\n2\n")],
        base_dir=tmp_path,
    )

    assert (target / "unsafe.csv").read_bytes() == b"x\n1\n"
    assert (target / "safe.csv").read_bytes() == b"y\n2\n"
