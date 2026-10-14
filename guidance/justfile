# kanon development tasks

check:
    uv run --with pyyaml python tools/validate.py
    uv run --with pyyaml python tools/manifest.py --check
    uv run --with pytest --with pyyaml python -m pytest -q

test:
    uv run --with pytest --with pyyaml python -m pytest -q

# regenerate sections/MANIFEST.yml + README/CONTRIBUTING vocabulary tables
manifest:
    uv run --with pyyaml python tools/manifest.py

drift:
    uv run --with pyyaml python tools/validate.py --drift

sources:
    uv run --with pyyaml python tools/validate.py --sources
