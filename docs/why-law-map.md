# Why law-map: organize law by the function it demands

## The problem

Regulatory compliance tooling usually mirrors the *form* of law: one table
per directive, one page per statute, one tickbox per certification. That
mirror breaks down the moment a product ships to several legal systems. The
Japanese statute, the EU regulation, and the US enforcement action each
*look* different, live in different document formats, and are maintained by
different institutions — yet a development team needs a single answer to one
question: *what must this system actually do?*

## The thesis: compare functions, not forms

Comparative law since Zweigert and Kötz argues that legal systems are best
compared at the level of the **function** a rule performs, not the doctrinal
form it takes: "the functional method starts from the question of what
*function* a legal institution fulfills" (Zweigert & Kötz, *Introduction to
Comparative Law*, 3rd ed., ch. 3). Two rules that solve the same social
problem for the same kind of actor are, functionally, the same rule even
when one sits in a statute, one in a regulation, and one in a court opinion.

law-map applies that method to engineering. A grounding is a jurisdiction
plus a pinpoint source (article, section, case). Several groundings with
different source types — statute, regulation, **precedent**, **guidance**,
standard, model code — attach to **one obligation node** whenever they
demand the same technical behavior. The obligation node is the unit of
engineering work:

```text
obligation.privacy.no-cleartext-pii-logging
├─ JP   statute    APPI 第23条 (安全管理措置)
├─ EU   regulation GDPR Art. 5(1)(f), Art. 32
├─ UK   statute    UK GDPR + DPA 2018
├─ US   statute    Cal. Civ. Code §1798.150
└─ US   precedent  FTC v. Wyndham; In re LabMD
```

Five documents, one deontic rule: *no cleartext personal identifiers in
logs*. The team implements the rule once; the groundings are the evidence a
reviewer (human or agent) uses to check it.

## Why precedent and guidance belong

Common-law systems bind through case law and administrative enforcement, not
only through enacted text. FTC Act § 5 is a short statute whose operative
content for software companies lives in decisions like *FTC v. Wyndham*.
Excluding precedent would silently drop the most enforceable common-law
constraints from the graph. Guidance (NIST SSDF, ICO logging guidance, METI
SBOM guides) is included with its status declared — *in_force, scheduled,
proposed, superseded* — and is tagged so readers can weigh binding force
without the graph pretending all sources carry equal weight. Scope,
`applicability`, and `status` fields keep groundings honest about who is
bound and how hard.

## The pipeline

```text
open-law ──> law-map ──> good-future-codex ──> python-copier-template ──> projects
scrape      organize       review prose           vendor                  generated
legislation deontic rules  human/AI-facing        AGENTS.md + CI gates    repos
```

1. **open-law** scrapes world legislation into unified Law objects. It
   answers "what does this instrument say".
2. **law-map** (this repo) answers "what must software do" — deontic rules
   as obligations, each with groundings, enforcement level (L0 prose / L1
   detection / L2 hard gate), machine-check refs, and a `review_by`
   freshness contract per grounding. `law-map check` keeps the graph honest:
   expired groundings fail CI; the weekly drift-watch workflow probes source
   URLs for 404s and redirects and files one issue.
3. **good-future-codex** contains the reviewed, human/AI-facing prose
   sections derived from the graph (`law-map export` produces the skeletons).
4. **python-copier-template** vendors the outcomes into generated
   repositories: AGENTS.md obligations and CI gates that enforce them.

## Design consequences

- **One obligation, many groundings.** Adding a jurisdiction is adding a
  grounding, not forking the engineering requirement.
- **Freshness as a first-class field.** Law changes; every grounding carries
  `review_by`, and drift is a periodic, watchable process.
- **Checks are data.** `enforcement.check_refs` links an obligation to
  `checks/<domain>/<slug>.yml`, so an obligation without a detection rule is
  visibly L1-less, and a rule without an obligation is orphaned.
- **Deterministic, offline, reviewable.** Everything except
  `law-map check --sources` is deterministic YAML in / YAML out, so the
  graph is safe to diff in code review.

## The boundary: this is not legal advice

law-map records *what instruments say and where they are pinned*. It does
not interpret them for a specific product, market, or dispute; it is a map
of obligations, not an opinion. The `review_by` contract exists precisely
because a map can go stale while the territory does not. For an actual
compliance determination, consult a qualified practitioner.