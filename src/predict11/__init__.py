"""predict11 — IPL Dream11 fantasy-XI predictor.

Pipeline: Cricsheet YAML -> DuckDB -> Dream11 scoring (labels) -> leak-safe
features -> LightGBM -> temporal backtest -> XI optimizer -> FastAPI.
"""

__version__ = "0.1.0"
