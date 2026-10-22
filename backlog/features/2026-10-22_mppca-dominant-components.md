---
id: "2026-10-22_mppca-dominant-components"
title: "MPPCA M-step: dominant components, cheap matrix side, stop early"
status: "In Progress"
priority: "High"
created: "2026-10-22"
last_updated: "2026-10-22"
category: "features"
related_cips: ["0012", "0015"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- compute
- mppca
- performance
- subject_grain
- cip0012
- cip0015
---

# Task: Stop paying for a full SVD in every MPPCA M-step

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Subject-grain EM on the Draghi packed corpus is slow because every M-step
asks LAPACK for **all** `min(n, d)` singular vectors of a weighted
`n × 3072` matrix, then throws most of them away. We do not need a full
SVD. We need the **dominant PPCA factors** — those with
`λ > σ²` — plus a 2-D Bishop–Tipping plane for the figure. Those are a
small leading subspace.

This task is a code survey plus the implementation plan to fix that, using
tricks that are already in scikit-learn (a referia dependency) rather than
a new stack. Do not start coding until this task is Ready / the approach
is accepted.

### Live scale (Draghi, 2026-10-22)

Packed `info/records.parquet`: **n = 1028 phrases**, **d = 3072**
(`text-embedding-3-large`). One corpus row. `em_accept` default 40.
`propose_split` default `n_restarts = 8`.

A dense economy SVD of a 1028 × 3072 matrix is ~`O(n² d) ≈ 3×10⁹`
flops **per component per iteration**, and we currently request every
left/right vector even though PPCA keeps only `q = #{λ_i > σ²}` of them.
Propose-split worst case is on the order of
`8 restarts × 40 iters × 2 children` full SVDs of that size, plus
k-means `n_init=10` in the same dimension, plus a second full SVD inside
`component_local_plane` when the model `q < 2`.

A timing job that went `parquet → pandas → np.stack` of 1028 Python
lists of 3072 floats **hung** before the first SVD. Materialising the
embedding matrix as an object array is itself broken; the M-step is
then worse.

## Code survey

All of this lives in referia. multilogue's `multilogue/mppca.py` is the
same algorithm (full `np.linalg.svd(Xw, full_matrices=False)`). Distance
MDS (`eigh` of a `n_docs × n_docs` Gram) is a different, small problem
and is out of scope.

### Call graph (every full SVD marked)

```
subject_grain_seed_fit / subject_grain_reset
  → mppca_fit                    # KMeans n_init=10, then EM
      → fit_weighted_ppca  ★ SVD  # once per topic per iter + final M-step
  → rebuild_uq_by_topic
      → local_uq_plotly_spec
          → component_local_plane ★ SVD again if q_model < q_viz=2

profile_topic_sigma2             # 10 σ² grid points
  → mppca_fit × 10               # σ²_mode=profile on 03_grain

subject_grain_propose_split
  → propose_split
      → mppca_fit × n_restarts   # default 8, max_iter=40, k=n_children
          → fit_weighted_ppca ★
      → fit_from_responsibilities(max_iter=0)  # one M-step, no E-loop
      → rebuild_uq_by_topic      # ★ possible second SVD per topic

fit_from_responsibilities        # same ★ SVD loop as mppca_fit (Undo redraw)
```

Sites of `np.linalg.svd(..., full_matrices=False)`:

| Function | Matrix | What is kept | What is discarded |
|---|---|---|---|
| `fit_weighted_ppca` | `Xw` `(n, d)` = `√w (x − μ)` | `Vt[λ > σ²].T` and those `λ` | `U` entirely; all `Vt` rows with `λ ≤ σ²` |
| `component_local_plane` | same `Xw` | at most **2** extra directions to pad the plot | the rest of the spectrum |
| `examples/subject_grain_uq/build_records.py` | bake helper | same pattern | same |

`full_matrices=False` is **not** truncated SVD. For `(n, d) = (1028, 3072)`
NumPy/LAPACK `*GESDD` still returns `K = min(n, d) = 1028` singular
values and a `Vt` of shape `(1028, 3072)`. There is no `n_components`.

### Efficient direction: we do not choose one

`Xw` is **wide** (`n < d`) on Draghi. The cheap Gram is the **n-side**
`Xw Xwᵀ` (1028 × 1028), not the d-side `Xwᵀ Xw` (3072 × 3072).

We never form either Gram. We hand the fat data matrix to `np.linalg.svd`
and hope GESDD picks the cheap side internally. Even if it does, it still
computes **all** 1028 eigenpairs of that Gram. PPCA then keeps the prefix
with `λ > σ²`.

Rule that should be explicit:

- If using a **dense** eigensolve, always work with
  `min(n, d) × min(n, d)` and lift the vectors back
  (`V = Xwᵀ U / s` when `n ≤ d`; `U = Xw V / s` when `n > d`).
- If using a **truncated / randomized** SVD, do not form a Gram at all.
  Range-finder cost is `O(n d q)` with `q ≪ min(n, d)`.

For Draghi, `n=1028`, `d=3072`, `q ~ 10–40` (order of magnitude):
randomized SVD is ~`O(n d q) ≈ 10⁸` flops versus ~`3×10⁹` for the full
economy SVD — tens of times cheaper **per M-step**, before counting
restarts.

When `n` later exceeds `d` (many more phrases), the cheap dense Gram
flips to the d-side. Truncated methods stay `O(n d q)` either way.
Write the helper so the side is a function of `(n, d, q)`, not a
hard-coded assumption that embeddings are always wide.

### k=1 is a special case we still overpay

For `k=1`, responsibilities are identically 1. The E-step cannot move.
`max |ΔR|` is 0 on iteration 1, so the *EM loop* already stops. We still:

1. Run sklearn `KMeans(n_clusters=1, n_init=10)` in 3072-d (pointless).
2. Pay two full SVDs (loop + final M-step) of 1028 × 3072.
3. May SVD again in `component_local_plane` for the plot.

Reset-to-k=1 therefore feels slow even though EM has nothing to do.

### Convergence we already have (and what we do not)

`mppca_fit` / `fit_from_responsibilities` stop on
`max |R_new − R| < 1e-5`. That L∞ test on responsibilities is stricter
than a likelihood plateau. The E-step **already** builds
`log_likelihood_ppca` per component; a relative change in
`sum logsumexp(log_joint)` is free and usually fires earlier.

A *separate* likelihood pass would be slower. Monitoring the quantity
we already have would not.

### Adjacent costs (same file, same click)

- **KMeans `n_init=10`** on `(n, 3072)` at every `mppca_fit` (seed, profile
  grid, each propose restart). sklearn 1.3+ is already a dependency.
- **`profile_topic_sigma2`**: 10 full fits when `sigma2_mode=profile`.
- **`propose_split` `n_restarts=8`**: up to eight independent
  `mppca_fit(..., max_iter=40)` on the parent mass subset.
- **Embedding materialisation**: `np.asarray(list-of-lists)` / pandas
  object columns. Convert once to C-contiguous `float64` of shape
  `(n, d)` (or keep float32 if we accept the rounding).

## Do we need the full SVD?

No. Tipping & Bishop MPPCA (1999) is a **q-factor** model per component.
The exact M-step given responsibilities is weighted PCA **truncated at
the noise floor**, not a complete spectral decomposition.

We need:

1. All eigenvectors with `λ > σ²` (for the Gaussian, `log_det`, and
   E-step). Missing one of those *does* change the model.
2. Two orthonormal directions for `q_viz=2` (plot), which may include
   factors *below* `σ²` when the model collapsed to `q=0` or `q=1`.

We do **not** need the rest of the spectrum, left singular vectors `U`,
or a square `Vt`.

If `σ²` is very small and `n` is large, `q` can grow. Cap it with an
explicit `max_q` (config / row field) and grow a truncated SVD until
the last returned `λ ≤ σ²` or `max_q` is hit. Document that hitting
`max_q` with `λ_min > σ²` is a model truncation, not a silent bug.

## Well-known tricks (in preference order)

Already in the environment unless noted. sklearn `>=1.3` is in
`pyproject.toml`. sklearn brings scipy.

1. **Randomized SVD (Halko, Martinsson, Tropp 2011)** —
   `sklearn.utils.extmath.randomized_svd(Xw, n_components=q, n_oversamples=10, random_state=...)`.
   Same kernel sklearn uses for `PCA(svd_solver="randomized")` and
   `TruncatedSVD`. Default first choice: no new dependency, handles both
   `n < d` and `n > d`, cost `O(n d q)`.

2. **Adaptive q** — start at `q0 = min(32, n-1, d-1)`; if the smallest
   returned `λ` is still `> σ²`, double `q` and retry (or one
   `svds`/`randomized_svd` with a generous cap). Stop when
   `s[-1]² / Σw ≤ σ²`.

3. **Thin Gram + `eigh` on `min(n, d)`** — only when
   `min(n, d)` is tiny (say `< 64`) or we must match legacy bit-for-bit
   tests. For Draghi `n=1028` this is still a 1028³ eigensolve if we
   keep *all* vectors; use it only as a correctness oracle against
   randomized SVD, not as the hot path.

4. **ARPACK / `scipy.sparse.linalg.svds`** — `k` leading pairs of a
   linear operator. Good when `q` is tiny and `n, d` huge. More
   brittle (solver params, which='LM') than randomized SVD. Optional
   backend, not the default.

5. **Tipping–Bishop inner EM on `W`** (the 1999 paper) — never SVD the
   data; iterate the factor-loading M-step for fixed `q`. Matches the
   original MPPCA derivation. More code, extra inner loops, easy to
   get `q` and `σ²` coupling wrong. Defer unless randomized SVD is
   not enough.

6. **Power / subspace iteration for the plot only** —
   `component_local_plane` needs two directions. A 2-D randomized range
   finder (or reuse `U_q` from the M-step) must replace the second full
   SVD.

7. **Skip k=1 KMeans**; **`n_init=1`** or `MiniBatchKMeans` for `k≥2`.
   sklearn already has both.

8. **Likelihood stop** — `Δℓ / n < ε` from the existing `log_joint`.
   Free. Complements, does not replace, truncated SVD.

9. **Do not add**: MATLAB `svds`, Facebook `fbpca`, Intel oneDAL,
   GPU CuPy, unless we later prove randomized SVD on CPU is the
   remaining bottleneck. Those fix the same math we can already call
   through sklearn.

10. **Do not** switch the M-step to sklearn `PCA` as a black box without
    wrapping weights: we need **weighted** PCA (`√wᵢ (xᵢ − μ)`). Passing
    unweighted `X` to `PCA.fit` is a model change. `randomized_svd(Xw)`
    is the correct hook.

### Packages that already solved “leading components of a fat matrix”

| Package | Use here? |
|---|---|
| **sklearn `randomized_svd` / `PCA(svd_solver="randomized")`** | Yes — already a dependency. Weighted via `Xw`. |
| **sklearn `TruncatedSVD`** | Same kernel; `randomized_svd` is the lower-level API we want. |
| **scipy `svds` / `eigsh`** | Optional backend. |
| **sklearn `MiniBatchKMeans`** | Init only. |
| **pyppca / random GitHub MPPCA** | No — unmaintained, would fork the model. |
| **fbpca, daal4py, cupy** | Not until sklearn's randomized SVD is the measured leftover. |

## Recommended design (after acceptance)

One helper, used by `fit_weighted_ppca` and `component_local_plane`:

```text
weighted_leading_ppca(X, w, sigma2, *, max_q, q_min=0, rng) -> U_q, lambdas_q
```

- Build `Xw` as today (`nan_to_num` stay).
- Choose algorithm:
  - `q_cap = min(max_q, n-1, d-1)`;
  - `randomized_svd` (default);
  - dense `eigh` on the cheap Gram only if `min(n, d) <= ~64` or
    `algorithm="full"` for tests.
- Retain `λ > σ²`, always return at least `q_min` columns when the
  caller is the plot (`q_min=2`).
- Keep the LinAlgError → jitter → isotropic fallback behaviour
  (current CIP-0012 guard).

Then, independently and cheaper:

- `mppca_fit`: if `k == 1`, skip KMeans; set `n_init=1` otherwise.
- Stop EM on relative log-likelihood as well as `ΔR`.
- `propose_split`: fewer restarts once local fits are stable; do not
  hide a second full SVD in the figure builder.
- Convert packed embeddings to `(n, d) float64` once at the compute
  boundary (`subject_grain_seed_fit` / propose / reset).

Bit-for-bit identity with today's `np.linalg.svd` is **not** required.
Match: row-stochastic `R`, `q` within ±1 of the full SVD on fixtures
with `n, d ≤ 32`, and plot planes that still show two axes.

## Acceptance Criteria

- [x] Survey above agreed (or amended in this file); no separate design doc
- [x] `fit_weighted_ppca` no longer calls full `np.linalg.svd` on the
      hot path; it requests a leading subspace with an explicit cheap
      side / randomized method
- [x] `component_local_plane` does not run a second full SVD
- [x] `k=1` does not run KMeans
- [x] EM can stop on relative log-likelihood using the existing E-step
      `log_joint` (no extra data pass)
- [x] Packed embeddings enter EM as a contiguous `(n, d)` float array
- [x] Tests: small dense SVD vs truncated helper on synthetic
      `(n, d) ≤ (40, 20)`; Draghi-shaped `(1028, 3072)` smoke test
      completes one k=1 M-step in well under a second on CPU; existing
      `tests/test_compute_mppca.py` still pass with loosened exact `U_q`
      equality where needed
- [x] 03_grain Propose / Reset remain the same buttons; no YAML schema
      change required except optional `max_q`

## Implementation Notes

- File: `referia/assess/compute/mppca.py`. Do not wait on lynguine.
- multilogue copy can stay stale until this lands; port later if at all.
- Optional YAML `max_q` on 03_grain EM parameters (next to `em_accept`)
  once the helper exists — not required for the first PR.
- Do not bump NumPy / add scipy as a direct extra unless `svds` becomes
  the chosen backend; sklearn is enough for randomized SVD.
- Keep `sigma2` as the truncation floor. Do not replace PPCA with
  ordinary PCA.

## Related

- CIP: 0012 (subject-grain Assess), 0015 (seed fit / reset)
- Code: `referia/assess/compute/mppca.py`
  (`fit_weighted_ppca`, `mppca_fit`, `propose_split`,
  `component_local_plane`)
- Twin: `multilogue/mppca.py` (same full SVD)
- sklearn: `sklearn.utils.extmath.randomized_svd`
- Paper: Halko, Martinsson, Tropp, *Finding structure with randomness*,
  SIAM Review 2011; Tipping & Bishop, *Mixtures of Probabilistic
  Principal Component Analysers*, Neural Computation 1999
- Live data: OneDrive
  `dialogue-analysis/draghi-competitiveness/info/records.parquet`
  (1028 × 3072)

## Progress Updates

### 2026-10-22

Task created as Proposed after 03_grain EM felt slow on the packed
Draghi corpus. Survey: full economy SVD on every M-step; no cheap-side
Gram; `U` discarded; Propose pays up to 8 × 40 child fits; k=1 still
runs KMeans; likelihood is already in the E-step and is not the
bottleneck. Timing via pandas object arrays hung before SVD.

Implementation started on `mppca-dominant-components`. Helper
`weighted_leading_ppca` uses sklearn `randomized_svd` (default when
`min(n, d) > 64`) or cheap-side Gram + `eigh`. `fit_weighted_ppca` and
`component_local_plane` no longer call `np.linalg.svd`. k=1 skips
KMeans and the E-loop. EM also stops on `|Δℓ|/n`. Packed embeddings
stack to C-contiguous float64. Default `max_q=128` is an explicit
factor cap (optional YAML still deferred). `tests/test_compute_mppca.py`
passes, including a 1028 × 3072 k=1 smoke test.
