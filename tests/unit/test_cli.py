import json

from data_agent_lab.cli.main import main


def test_bench_manifest_cli_writes_infiagent_manifest(tmp_path):
    csv_path = tmp_path / "data" / "sample.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text("x\n1\n", encoding="utf-8")
    source = tmp_path / "tasks.jsonl"
    source.write_text(
        json.dumps(
            {
                "id": "cli-demo",
                "question": "What is x?",
                "csv_path": "data/sample.csv",
                "expected": "1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "benchmark_manifest.json"

    code = main(
        [
            "bench",
            "manifest",
            "--adapter",
            "infiagent",
            "--source",
            str(source),
            "--root",
            str(tmp_path),
            "--output",
            str(output),
            "--subset",
            "demo",
        ]
    )

    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["tasks"][0]["id"] == "cli-demo"
    assert payload["tasks"][0]["csv_path"] == "data/sample.csv"
    assert payload["tasks"][0]["subset"] == "demo"
