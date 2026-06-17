# Data-Agent-Lab

**验证原生的可复现数据分析 Agent · Verification-native reproducible data analysis agent**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 项目简介 | About

| | |
|---|---|
| **中文名** | **Data-Agent-Lab（数据智能体实验台）** |
| **English** | **Data-Agent-Lab** |
| **一句话（中文）** | 面向本地 CSV / SQLite / DuckDB 的数据分析 Agent：写 SQL、做验证、留证据、出可复现报告。 |
| **One-liner (EN)** | A local data analysis agent that writes SQL, validates every answer, and ships a reproducible evidence package. |

**中文**

Data-Agent-Lab 不是「会聊天的 SQL 工具」，而是一个 **验证原生（verification-native）** 的数据分析工作台。每个答案在输出前都要经过确定性检查（聚合粒度、结果 shape、计划语义等），并自动生成报告、验证日志、pytest evaluator 和完整 audit trail，方便复现与 benchmark 评测。

**English**

Data-Agent-Lab is not a chatbot that happens to run SQL. It is a **verification-native** analysis workbench: every answer passes deterministic checks (aggregation grain, result shape, plan semantics) before release, and each run exports a report, validation log, pytest evaluator, and evidence ledger for reproducibility and benchmarking.

---

## 核心特性 | Features

| 中文 | English |
|------|---------|
| 数据接入与 Profiling（CSV / SQLite / DuckDB） | Ingestion & profiling for CSV, SQLite, DuckDB |
| 计划语义引擎 PSE（拦截错误聚合粒度等） | Plan Semantics Engine (PSE) — blocks bad aggregation grain |
| DuckDB 只读 SQL + 完整 run artifacts | Read-only DuckDB SQL + full run artifacts |
| Benchmark 适配器：golden / InfiAgent / DataAgentBench | Benchmark adapters: golden, InfiAgent, DAB |
| CLI + 可选 Streamlit 工作台 | CLI + optional Streamlit workbench |

---

## 安装 | Install

```bash
git clone https://github.com/YOUR_USERNAME/Data-Agent-Lab.git
cd Data-Agent-Lab
pip install -e ".[dev]"

# 可选 UI | Optional UI
pip install -e ".[ui]"
```

---

## 快速开始 | Quick Start

```bash
# 数据 Profiling | Profile data
dal profile examples/csv_revenue/data

# 运行分析 | Run analysis
dal analyze --question "What was Electronics revenue in 2024-02?" --data examples/csv_revenue/data

# Golden benchmark（真实 Agent）| Golden benchmark (real agent)
dal bench run --adapter golden --agent analyze --tag core

# Streamlit 工作台 | Streamlit workbench
streamlit run data_agent_lab/ui/streamlit_app.py
```

---

## 项目结构 | Layout

```text
data_agent_lab/
  catalog/          # 接入、profiling、fingerprint | ingestion, profiling
  agents/           # 规划、SQL 生成、流水线 | planner, pipeline
  validation/       # PSE、检查器、evaluator | PSE, validators
  benchmarks/       # golden / infiagent / dab 适配器
  reporting/        # Markdown + HTML 报告
  runtime/          # run 目录与 ledger
  cli/              # dal profile | analyze | bench
  ui/               # Streamlit
tests/golden/       # 回归任务 | regression tasks
docs/               # 设计文档 | design docs
```

---

## 文档 | Documentation

- [PROJECT_DESIGN.md](docs/PROJECT_DESIGN.md) — 项目设计（English）
- [PROJECT_DESIGN.zh-CN.md](docs/PROJECT_DESIGN.zh-CN.md) — 项目设计（中文）
- [EVALUATION_STRATEGY.md](docs/EVALUATION_STRATEGY.md) — 评测与 benchmark 策略

---

## GitHub 仓库信息 | Repository Metadata

**Recommended repo name:** `Data-Agent-Lab`

**Description (GitHub About — English, ≤350 chars):**

> Verification-native data analysis agent for local CSV/SQLite/DuckDB. Validates SQL results, exports reproducible evidence packages, and includes benchmark adapters for golden tasks, InfiAgent-DABench, and DataAgentBench.

**简介（GitHub About — 中文，供复制）：**

> 面向本地 CSV/SQLite/DuckDB 的验证原生数据分析 Agent。自动验证 SQL 结果，导出可复现证据包，内置 golden / InfiAgent / DataAgentBench benchmark 适配器。

**Topics / 标签建议:**

`data-agent` `data-analysis` `duckdb` `sql-agent` `verification` `reproducibility` `benchmark` `llm-agent` `data-quality`

---

## 状态 | Status

Core MVP（S0–S3）已实现，无需 LLM API 即可跑通 golden benchmark（6/6 pass）。

Stretch：外部 LLM planner、LangGraph 编排、回归/异常检测、完整 DAB 多库支持。

---

## License

MIT — see [LICENSE](LICENSE).
