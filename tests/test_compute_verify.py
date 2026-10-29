"""CIP-001F: bag-of-words reconstruction of discrete phrase codes."""

from referia.assess.compute.verify import hard_lens_labels, run_kind_reconstruction


def _separable(n_each=24):
    phrases = (
        ["worry about privacy and harm"] * n_each
        + ["this helps staff save time"] * n_each
        + ["only if the cost is low"] * n_each
    )
    kinds = (
        ["concern"] * n_each + ["benefit"] * n_each + ["condition"] * n_each
    )
    docs = (
        [f"c{i % 8}" for i in range(n_each)]
        + [f"b{i % 8}" for i in range(n_each)]
        + [f"d{i % 8}" for i in range(n_each)]
    )
    groups = (
        ["chatbot"] * n_each + ["workshop"] * n_each + ["chatbot"] * n_each
    )
    return phrases, kinds, docs, groups


def test_separable_kinds_are_reconstructable():
    phrases, kinds, docs, groups = _separable()
    summary, confusion, coefs, flags, md, n = run_kind_reconstruction(
        phrases,
        kinds,
        doc_ids=docs,
        groups=groups,
        n_folds=4,
        seed=0,
        min_df=1,
        max_features=200,
        verified_only=False,
    )
    assert n == 72
    assert summary["accuracy_mean"] > 0.85
    assert summary["permutation_accuracy"] < summary["accuracy_mean"] - 0.3
    assert any(c["n"] > 0 for c in confusion)
    assert coefs  # logreg ngrams
    assert "siding" in md.lower()
    codes = {f["code"] for f in flags}
    assert "near_chance" not in codes


def test_shuffled_labels_near_chance():
    phrases, _kinds, docs, _groups = _separable(n_each=30)
    # Round-robin labels, independent of the three cue-word blocks.
    rng_kinds = ["concern", "benefit", "condition"] * 30
    summary, _cm, _coef, flags, _md, n = run_kind_reconstruction(
        phrases,
        rng_kinds,
        doc_ids=docs,
        n_folds=3,
        seed=1,
        min_df=1,
        max_features=200,
        verified_only=False,
    )
    assert n == 90
    assert summary["accuracy_mean"] < 0.55
    codes = {f["code"] for f in flags}
    assert "near_chance" in codes or "class_collapse" in codes


def test_verified_only_drops_unverified():
    phrases = ["worry a", "helps b", "if c"] * 10
    kinds = ["concern", "benefit", "condition"] * 10
    verified = [True, False, True] * 10
    summary, _cm, _coef, _flags, md, n = run_kind_reconstruction(
        phrases,
        kinds,
        verified=verified,
        verified_only=True,
        n_folds=2,
        seed=0,
        min_df=1,
    )
    assert summary["n_dropped_unverified"] == 10
    assert n == 20
    assert "unverified" in md.lower() or n == 20


def test_too_few_phrases_explains_itself():
    summary, confusion, coefs, flags, md, n = run_kind_reconstruction(
        ["one"],
        ["concern"],
        n_folds=5,
        missing_hint="Run 07_grounds Classify all + Save first.",
    )
    assert n < 5
    assert confusion == []
    assert coefs == []
    assert flags == []
    assert "Not enough" in md
    assert "Run 07_grounds Classify all + Save first." in md
    assert summary["n_kept"] == 1


def test_label_name_appears_in_markdown():
    phrases, kinds, docs, groups = _separable()
    summary, _cm, _coef, _flags, md, n = run_kind_reconstruction(
        phrases,
        kinds,
        doc_ids=docs,
        groups=groups,
        n_folds=4,
        seed=0,
        min_df=1,
        max_features=200,
        verified_only=False,
        label_name="basis",
    )
    assert n == 72
    assert summary["label_name"] == "basis"
    assert "basis reconstruction" in md.lower()
    assert "Per-basis" in md


def test_hard_lens_labels_argmax():
    codebook_r = [[1.0, 0.0], [0.0, 1.0]]
    labels = hard_lens_labels(
        codebook_r, [0, 0, 1], {"T0": "privacy", "T1": "speed"}
    )
    assert labels == ["privacy", "privacy", "speed"]
    phrase_r = [[0.1, 0.9], [0.8, 0.2]]
    labels = hard_lens_labels(phrase_r, None, {"T0": "A", "T1": "B"})
    assert labels == ["B", "A"]


def test_nb_model_runs():
    phrases, kinds, _docs, _groups = _separable(n_each=12)
    summary, _cm, coefs, _flags, _md, n = run_kind_reconstruction(
        phrases,
        kinds,
        model="nb",
        n_folds=3,
        seed=0,
        min_df=1,
        verified_only=False,
    )
    assert n == 36
    assert summary["model"] == "nb"
    assert summary["accuracy_mean"] > 0.7
    assert coefs == []
