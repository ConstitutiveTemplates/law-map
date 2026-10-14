# law-map development tasks
# `just check` = validate corpus + README stats sync + pytest + ruff + mypy

check:
    uv run law-map validate
    uv run law-map stats --markdown --check README.md
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

# regenerate the README "Scope today" block from the corpus
stats:
    uv run law-map stats --markdown --write README.md

# pipeline: upstream→downstream order — validate corpus, then review-freshness check.
pipeline:
    uv run law-map validate && uv run law-map check --days 30

drift:
    uv run law-map check --sources --days 30

# law-watch: were cited instruments amended after their reviewed_on/effective? (network)
watch:
    uv run law-map watch
