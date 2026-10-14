"""Section-corpus validation, split by responsibility.

- :mod:`validation.const` — paths, front matter contract, patterns, probe constants
- :mod:`validation.vocabulary` — when / placement / status vocabulary (VOCABULARY.yml)
- :mod:`validation.frontmatter` — YAML front matter / body split
- :mod:`validation.manifest` — generated MANIFEST.yml and docs vocabulary tables
- :mod:`validation.report` — shared error/warning sinks
- :mod:`validation.corpus` — front matter / body / review_by / MANIFEST-sync checks
- :mod:`validation.sources` — declared-URL collection (offline)
- :mod:`validation.probe` — curl HEAD/GET probing (network)
- :mod:`validation.upstream` — law-map / open-law grounding lookup
- :mod:`validation.liveness` — probe orchestration, flagging, drift output
- :mod:`validation.cli` — argparse entry point
"""
