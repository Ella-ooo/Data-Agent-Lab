#!/usr/bin/env bash
# Create GitHub repo and push (requires: gh auth login)
set -euo pipefail

REPO_NAME="${1:-Data-Agent-Lab}"
VISIBILITY="${2:-public}"

if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI: brew install gh"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Please login first: gh auth login"
  exit 1
fi

cd "$(dirname "$0")/.."

gh repo create "$REPO_NAME" \
  --"$VISIBILITY" \
  --source=. \
  --remote=origin \
  --description "Verification-native data analysis agent for local CSV/SQLite/DuckDB with reproducible evidence packages and benchmark adapters." \
  --push

echo ""
echo "Done. Set GitHub About (中文) in repo Settings:"
echo "验证原生数据分析 Agent：本地 CSV/SQLite/DuckDB，自动验证 SQL 结果，导出可复现证据包，内置 benchmark 适配器。"
echo ""
echo "Suggested topics: data-agent data-analysis duckdb verification reproducibility benchmark sql-agent"
