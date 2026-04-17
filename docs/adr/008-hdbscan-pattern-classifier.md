# ADR 008: HDBSCAN over Qwen3 embeddings for the Learn layer

## Status
Accepted

## Context
The Learn layer (Business Plan v4.5 §4.1.2) takes normalised observation
events and must produce a ranked list of **workflow candidates** — stable,
repeated action sequences performed by three or more employees — that
can be surfaced to the Propose layer.

Properties of the input:

- Event sequences are variable-length (5 to ~50 steps), noisy, and
  interleaved across employees.
- The "number of distinct workflows" is unknown up front; workflow
  discovery is the point.
- Some sequences are one-offs; those must be rejected, not forced into a
  cluster.
- Outputs must be explainable — auditors and works councils ask "why
  was this pattern detected?" and we have to answer.

Options considered:

1. **k-means** over sequence embeddings. Requires k to be known and
   forces every point into a cluster.
2. **DBSCAN** — density-based, handles noise, but requires a global
   `eps` parameter that is brittle across tenants of different size.
3. **HDBSCAN** — hierarchical extension of DBSCAN. Chooses the clustering
   at variable densities; labels low-density points as noise (-1); no
   global `eps` to tune.
4. **Graph clustering (e.g. Louvain)** over a sequence-similarity graph.
   Powerful but O(n²) similarity computation; scaling concerns.
5. **Sequence-mining algorithms (PrefixSpan, GSP)** directly on action
   sequences. Skips the embedding step; produces interpretable patterns
   but doesn't handle near-identical-but-not-equal sequences well.

Embedding backbone options:

a. **Qwen3-30B-A3B** — already the planner model (ADR 004); reusing
   its embedding output means we don't ship a second giant model.
b. **Sentence-BERT / MiniLM** — smaller, cheaper, general-purpose.
c. **Custom sequence encoder** trained on our data — not feasible at
   MVP scale.

## Decision
Use **HDBSCAN** on **Qwen3-30B-A3B embeddings** of serialised event
sequences, with three hard gates after clustering:

1. `MIN_EMPLOYEE_AGGREGATION = 3` — reject clusters with fewer than 3
   distinct employee contributors (privacy gate, also ADR 009).
2. `MIN_OBSERVATION_WINDOW_DAYS = 14` — reject clusters observed over
   <14 days (stability gate).
3. `MIN_PATTERN_RECURRENCE = 5` — reject clusters with <5 total
   occurrences (signal-to-noise gate).

All three live as module-level constants in
`services/pattern-classifier/src/constraints.py` with unit tests asserting
the exact values.

## Rationale
- **HDBSCAN handles variable densities** without per-tenant tuning.
  A small tenant (~30 employees) and a large one (~3000) can share the
  same clusterer configuration; HDBSCAN picks the appropriate density
  automatically.
- **Noise labelling is a feature.** Employees who do one-off work that
  looks like nothing else get a `-1` label and are naturally excluded
  from proposals — which is what the k≥3 gate wants anyway.
- **Qwen3 embeddings reuse a model we already serve.** Running sequences
  through the planner model's embedding head is marginal compute cost on
  hardware we already have (ADR 004), and the semantic quality is
  meaningfully better than MiniLM on business-workflow text.
- **Explainability.** HDBSCAN yields a condensed cluster tree; each
  workflow candidate can be traced back to (a) its cluster ID, (b) its
  medoid sequence, (c) the contributing employees (as anonymised
  actor_ids), (d) the stability score. That is enough for the Propose
  layer to show an auditable "why" card.
- **Three-gate structure makes the compliance constraints legible.**
  The aggregation gate is not a knob — it's a named, tested constant
  with a DB-level CHECK mirror in `proposals.employee_count >= 3`. This
  matches the Business Plan §11A.5 requirement that aggregation be
  architectural, not configurable.

## Consequences
- **hdbscan requires a C compiler** at install time (it wraps a Cython
  extension). Dockerfile already includes `build-essential` — documented.
- **Cluster membership is not stable across reruns** if the input
  distribution shifts. We store cluster IDs with a salted hash of the
  medoid sequence so downstream proposal identity doesn't break.
- **Qwen3 embedding-head latency** is non-trivial (hundreds of ms per
  sequence). The classifier runs as a daily batch, not online, and
  batches embeddings 64-at-a-time to keep GPU utilisation high.
- **We must explain the clustering output** to non-ML reviewers. The
  Propose layer ships a per-candidate "why" card showing the medoid
  sequence, contributor count, and stability score.

## Alternatives and why they were rejected
- *k-means* — requires k up front; forces every event into a cluster
  (including one-offs that should be noise).
- *DBSCAN* — global `eps` too brittle across tenant sizes.
- *Sequence-mining* — poor handling of near-duplicate sequences;
  interpretability advantage doesn't outweigh flexibility cost.

## References
- Business Plan v4.5 §4.1.2 (Learn layer), §11A.5 (privacy gates).
- ADR [004](004-qwen3-planner-model.md) (embedding backbone).
- [services/pattern-classifier/src/constraints.py](../../services/pattern-classifier/src/constraints.py)
- [services/pattern-classifier/src/classifier.py](../../services/pattern-classifier/src/classifier.py)
