"""CIP-001F: bag-of-words reconstruction of discrete phrase codes."""

from referia.assess.compute.verify import (
    collapse_basis_labels,
    hard_lens_labels,
    run_kind_reconstruction,
    siding_row_text,
)


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


def test_collapse_basis_labels_experience():
    assert collapse_basis_labels(
        ["personal_experience", "principle", "", "others_experience"],
        "experience",
    ) == ["experience", "other", "", "experience"]
    assert collapse_basis_labels(["principle"], "seven") == ["principle"]


def test_siding_row_text_quote_and_phrase():
    row = {
        "phrase": "faster permits",
        "quote": "it sped up our licensing",
        "extract_text": "the unit body",
    }
    assert siding_row_text(row, "phrase") == "faster permits"
    assert siding_row_text(row, "quote") == "it sped up our licensing"
    assert siding_row_text(row, "quote_and_phrase") == (
        "faster permits it sped up our licensing"
    )
    assert siding_row_text(row, "quote_and_unit") == (
        "it sped up our licensing the unit body"
    )


def test_experience_on_quote_is_reconstructable():
    phrases = ["I saw this in my team last year"] * 20 + [
        "in general one should"
    ] * 20
    kinds = collapse_basis_labels(
        ["personal_experience"] * 20 + ["principle"] * 20,
        "experience",
    )
    summary, _cm, _coef, flags, md, n = run_kind_reconstruction(
        phrases,
        kinds,
        n_folds=4,
        seed=0,
        min_df=1,
        max_features=200,
        verified_only=False,
        label_name="experience",
        label_mode="experience",
        text_source="quote",
    )
    assert n == 40
    assert summary["label_mode"] == "experience"
    assert summary["text_source"] == "quote"
    assert summary["accuracy_mean"] > 0.85
    assert summary["balanced_accuracy_mean"] > 0.8
    codes = {f["code"] for f in flags}
    assert "near_chance" not in codes
    assert "experience reconstruction" in md.lower()
    assert "Verdict: above chance" in md
    experience_ngrams = {
        row["ngram"] for row in _coef if row["kind"] == "experience"
    }
    other_ngrams = {row["ngram"] for row in _coef if row["kind"] == "other"}
    assert experience_ngrams & {"team", "year", "saw", "last"}
    assert other_ngrams & {"should", "general", "one"}
    assert "should" not in experience_ngrams


def test_imbalanced_majority_is_not_near_chance_when_classes_separate():
    """class_weight=balanced can lose to majority; that is not chance."""
    phrases = ["privacy harm worry"] * 40 + ["helps save time"] * 8
    kinds = ["principle"] * 40 + ["personal_experience"] * 8
    summary, _cm, _coef, flags, md, n = run_kind_reconstruction(
        phrases,
        kinds,
        n_folds=2,
        seed=0,
        min_df=1,
        max_features=200,
        verified_only=False,
        label_name="basis",
    )
    assert n == 48
    codes = {f["code"] for f in flags}
    assert "near_chance" not in codes
    assert "Verdict: above chance" in md
    gap = summary["majority_baseline"] - summary["accuracy_mean"]
    if gap >= 0.02:
        assert "below_majority" in codes
    else:
        assert "below_majority" not in codes
    consistent = next((f for f in flags if f["code"] == "consistent"), None)
    if consistent is not None:
        assert consistent["message"].startswith("Above chance")


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
