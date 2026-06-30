"""Statistical modeling helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import statsmodels.api as sm


@dataclass
class RegressionResult:
    preview: list[dict]
    output_csv: Path | None
    error: str | None = None


def run_linear_regression(
    conn: duckdb.DuckDBPyConnection,
    *,
    table: str,
    target: str,
    features: list[str],
    output_csv: Path | None = None,
) -> RegressionResult:
    if not target or not features:
        return RegressionResult(preview=[], output_csv=None, error="Regression target or features missing")
    cols = [target, *features]
    select_cols = ", ".join(f'"{c}"' for c in cols)
    df = conn.execute(f"SELECT {select_cols} FROM {table}").fetchdf().dropna()
    if len(df) <= len(features) + 1:
        return RegressionResult(preview=[], output_csv=None, error="Not enough rows for regression")

    y = df[target]
    x = sm.add_constant(df[features], has_constant="add")
    model = sm.OLS(y, x).fit()
    rows = []
    for feature in features:
        rows.append(
            {
                "feature": feature,
                "coef": float(model.params[feature]),
                "pvalue": float(model.pvalues[feature]),
                "abs_coef": abs(float(model.params[feature])),
            }
        )
    rows.sort(key=lambda r: r["abs_coef"], reverse=True)
    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        import pandas as pd

        pd.DataFrame(rows).to_csv(output_csv, index=False)
    return RegressionResult(preview=rows, output_csv=output_csv)
