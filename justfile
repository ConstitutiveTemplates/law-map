# law-map development tasks
# `just check` = validate corpus + manifest sync + README stats sync + pytest + ruff + mypy + basedpyright

check:
    uv run law-map validate
    uv run law-map manifest --check
    uv run law-map stats --markdown --check README.md
    uv run pytest -q
    uv run ruff check .
    uv run mypy src/law_map
    uv run basedpyright

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

# regenerate guidance/sections/MANIFEST.yml from section front matter
manifest:
    uv run law-map manifest

# pipeline: upstream→downstream order — validate corpus, then review-freshness check.
pipeline:
    uv run law-map validate && uv run law-map check --days 30

drift:
    uv run law-map check --sources --days 30

# law-watch: were cited instruments amended after their reviewed_on/effective? (network)
watch:
    uv run law-map watch
