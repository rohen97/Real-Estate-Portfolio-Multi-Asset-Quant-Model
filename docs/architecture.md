# Architecture

React/Vite presentation calls a FastAPI service. Domain calculations are isolated in packages/domain. Synthetic files are deterministic; audit/API interfaces expose evidence, model version, seed and cache key. SQLite/DuckDB/Parquet are replaceable production boundaries.
