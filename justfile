# law-map development tasks
# `just check` = validate corpus + pytest + ruff + mypy

check:
    uv run law-map validate
    uv run pytest -q
    uv run ruff check .
    uv run mypy src/law_map

fmt:
    uv run ruff format .
    uv run ruff check --fix .

test:
    uv run pytest

validate:
    uv run law-map validate

# pipeline: upstream→downstream order — validate corpus, then review-freshness check.
pipeline:
    uv run law-map validate && uv run law-map check --days 30

drift:
    uv run law-map check --sources --days 30