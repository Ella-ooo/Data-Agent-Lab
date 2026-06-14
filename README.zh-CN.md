# Data-Agent-Lab · 数据智能体实验台

[English README](README.md)

## 项目名称

| 字段 | 内容 |
|------|------|
| **GitHub 仓库名** | `Data-Agent-Lab` |
| **中文展示名** | 数据智能体实验台 |
| **英文展示名** | Data-Agent-Lab |
| **定位** | 验证原生、可复现优先的本地数据分析 Agent |

## 一句话介绍

**中文：** 读取本地 CSV/SQL 数据，自动生成 SQL、验证结果、输出可复现分析报告的数据智能体。

**English:** A verification-native agent that reads local CSV/SQL data, writes SQL, validates results, and exports reproducible reports.

## 详细简介

Data-Agent-Lab 解决的是常见 data agent「答案流畅但不可靠」的问题。项目把每个分析结论当作需要证据支持的 claim，在输出前强制执行：

- 数据 profiling 与 value grounding
- 计划语义验证（PSE）：聚合粒度、操作完整性、禁止无依据 LIMIT
- SQL 执行与结果 shape 检查
- Workflow 复现检查与 claim 审查
- 自动生成 Markdown/HTML 报告、validation log、pytest evaluator

同时提供与 agent 开发并行的 **benchmark adapter** 框架，支持内部 golden tasks、InfiAgent-DABench manifest、DataAgentBench SQLite/DuckDB 子集。

## 适用场景

- 本地 CSV / SQLite / DuckDB 的描述性分析与数据质量检查
- 需要 audit trail 和可复现包的数据分析实验
- Data agent benchmark 评测与回归测试

## 快速命令

```bash
pip install -e ".[dev]"

dal profile examples/csv_revenue/data
dal analyze -q "What was Electronics revenue in 2024-02?" --data examples/csv_revenue/data
dal bench run --adapter golden --agent analyze --tag core
```

## GitHub 仓库设置建议

**About 描述（中文，复制到 GitHub）：**

> 验证原生数据分析 Agent：本地 CSV/SQLite/DuckDB，自动验证 SQL 结果，导出可复现证据包，内置 benchmark 适配器。

**About description (English):**

> Verification-native data analysis agent for local CSV/SQLite/DuckDB with reproducible evidence packages and benchmark adapters.

**推荐 Topics：**

`data-agent` `data-analysis` `duckdb` `verification` `reproducibility` `benchmark` `sql-agent`
