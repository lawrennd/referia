"""Label reconstruction sidings (CIP-001F).

Bag-of-words classifiers try to recover discrete codes from phrase text:
extract ``kind``, grounds ``basis``, or hard grain lens. High but imperfect
out-of-fold accuracy means the coding applied a stable lexical rule.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

import numpy as np

from .distance import _jsonable

__all__ = [
    "EXPERIENCE_BASES",
    "collapse_basis_labels",
    "hard_lens_labels",
    "run_kind_reconstruction",
    "siding_row_text",
]

MODELS = ("logreg", "nb", "linearsvc")
EXPERIENCE_BASES = ("personal_experience", "others_experience")
TEXT_SOURCE_LABELS = {
    "phrase": "phrase text",
    "quote": "quote text",
    "quote_and_phrase": "phrase plus quote",
    "quote_and_unit": "quote plus unit extract_text",
}


def collapse_basis_labels(kinds, mode: str = "seven") -> list[str]:
    """Map Part B bases to the paper's experience-vs-rest coding.

    ``seven`` keeps the seven-way labels. ``experience`` (alias ``binary``)
    collapses ``personal_experience`` and ``others_experience`` to
    ``experience`` and every other non-empty basis to ``other``.
    """
    mode = str(mode or "seven").strip().lower()
    raw = [str(k).strip() if k is not None else "" for k in list(kinds or [])]
    if mode not in {"experience", "binary"}:
        return raw
    out = []
    for label in raw:
        if not label:
            out.append("")
        elif label in EXPERIENCE_BASES:
            out.append("experience")
        else:
            out.append("other")
    return out


def siding_row_text(row: dict | None, source: str = "phrase") -> str:
    """Text the reconstruction vectoriser sees for one phrase row."""
    row = row or {}
    source = str(source or "phrase").strip().lower()
    phrase = str(row.get("phrase") or "").strip()
    quote = str(row.get("quote") or "").strip()
    unit = str(row.get("extract_text") or row.get("text") or "").strip()
    if source == "quote":
        return quote or phrase
    if source in {"quote_and_phrase", "phrase_and_quote"}:
        return " ".join(part for part in (phrase, quote) if part)
    if source in {"quote_and_unit", "unit"}:
        return " ".join(part for part in (quote, unit) if part) or phrase
    return phrase


def _as_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return int(default)
    try:
        f = float(value)
    except (TypeError, ValueError):
        return int(default)
    if not np.isfinite(f):
        return int(default)
    return int(f)


def _as_float(value: Any, default: float) -> float:
    if value is None or value == "":
        return float(default)
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not np.isfinite(f):
        return float(default)
    return f


def _as_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return bool(default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _md_table(rows: list[dict], columns: list[tuple[str, str]], *, ndigits=3) -> str:
    head = "| " + " | ".join(title for title, _ in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        cells = []
        for _, key in columns:
            val = row.get(key, "")
            if isinstance(val, float):
                cells.append(f"{val:.{ndigits}f}")
            else:
                cells.append(str(val))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def _vectorizer(model: str, *, ngram_min, ngram_max, min_df, max_features):
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

    ngram = (ngram_min, ngram_max)
    kwargs = dict(
        ngram_range=ngram,
        min_df=min_df,
        max_features=max_features,
        lowercase=True,
    )
    if model == "nb":
        return CountVectorizer(**kwargs)
    return TfidfVectorizer(**kwargs)


def _classifier(model: str, *, C: float, seed: int):
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.svm import LinearSVC

    if model == "nb":
        return MultinomialNB()
    if model == "linearsvc":
        return LinearSVC(
            C=C,
            class_weight="balanced",
            max_iter=2000,
            random_state=seed,
        )
    from sklearn.multiclass import OneVsRestClassifier

    return OneVsRestClassifier(
        LogisticRegression(
            C=C,
            class_weight="balanced",
            solver="liblinear",
            max_iter=300,
            random_state=seed,
        )
    )


def _oof(clf, X, y, splits):
    from sklearn.base import clone
    from sklearn.metrics import accuracy_score, balanced_accuracy_score

    y_hat = np.empty(len(y), dtype=object)
    accs = []
    bals = []
    for train, test in splits:
        est = clone(clf)
        est.fit(X[train], y[train])
        pred = est.predict(X[test])
        y_hat[test] = pred
        accs.append(accuracy_score(y[test], pred))
        bals.append(balanced_accuracy_score(y[test], pred))
    return y_hat, np.asarray(accs, float), np.asarray(bals, float)


def _logreg_coef_by_class(clf, class_names: Sequence[str]):
    """Return ``(coef, labels)`` with one coefficient row per class.

    Binary One-vs-Rest and binary ``LogisticRegression`` store a single
    coefficient vector for ``classes_[1]``. Mapping that row onto
    ``classes_[0]`` attributes principle language to experience.
    """
    raw_labels = getattr(clf, "classes_", None)
    if raw_labels is None:
        labels = list(class_names)
    else:
        labels = list(raw_labels)
    if hasattr(clf, "estimators_") and clf.estimators_:
        coef = np.vstack(
            [np.asarray(est.coef_, float).ravel() for est in clf.estimators_]
        )
    elif hasattr(clf, "coef_"):
        coef = np.asarray(clf.coef_, dtype=float)
        if coef.ndim == 1:
            coef = coef.reshape(1, -1)
    else:
        return None, []
    if coef.ndim != 2:
        return None, []
    if coef.shape[0] == 1 and len(labels) == 2:
        coef = np.vstack([-coef[0], coef[0]])
    return coef, labels


def _top_logreg_ngrams(clf, vec, class_names: Sequence[str], k: int = 8) -> list[dict]:
    if clf is None or vec is None:
        return []
    names = np.asarray(vec.get_feature_names_out())
    coef, labels = _logreg_coef_by_class(clf, class_names)
    if coef is None:
        return []
    rows = []
    for i, label in enumerate(labels):
        if i >= coef.shape[0]:
            break
        order = np.argsort(coef[i])[::-1][:k]
        for j in order:
            rows.append(
                {
                    "kind": str(label),
                    "ngram": str(names[j]),
                    "weight": round(float(coef[i, j]), 3),
                }
            )
    return rows


def run_kind_reconstruction(
    phrases,
    kinds,
    *,
    groups=None,
    doc_ids=None,
    verified=None,
    phrase_ids=None,
    n_folds: int = 5,
    seed: int = 0,
    model: str = "logreg",
    ngram_min: int = 1,
    ngram_max: int = 2,
    min_df: int = 2,
    max_features: int = 4000,
    C: float = 1.0,
    verified_only: bool = True,
    label_name: str = "kind",
    missing_hint: str = "Run 02_embed first.",
    **_kwargs,
) -> tuple:
    """Recover a discrete label from phrase text with bag-of-words CV.

    ``kinds`` is the label vector (extract kind, grounds basis, or hard
    lens). Returns ``summary, confusion, coefs, flags, markdown, n_kept``.
    Phrase text is not written to the summary (phrase_ids of out-of-fold
    errors only).
    """
    label_name = str(label_name or "kind").strip() or "kind"
    missing_hint = str(missing_hint or "Run 02_embed first.")
    model = str(model or "logreg").strip().lower()
    if model not in MODELS:
        model = "logreg"
    n_folds = max(2, _as_int(n_folds, 5))
    seed = _as_int(seed, 0)
    ngram_min = max(1, _as_int(ngram_min, 1))
    ngram_max = max(ngram_min, _as_int(ngram_max, 2))
    min_df = max(1, _as_int(min_df, 2))
    max_features = max(32, _as_int(max_features, 4000))
    C = max(1e-3, _as_float(C, 1.0))
    verified_only = _as_bool(verified_only, True)
    text_source = str(_kwargs.get("text_source") or "").strip().lower()
    label_mode = str(_kwargs.get("label_mode") or "").strip().lower()

    raw_phrases = list(phrases or [])
    raw_kinds = [str(k).strip() if k is not None else "" for k in list(kinds or [])]

    verified_list = list(verified) if verified is not None else None
    keep = []
    n_unverified = 0
    n_empty = 0
    for i in range(len(raw_phrases)):
        kind = raw_kinds[i] if i < len(raw_kinds) else ""
        text = str(raw_phrases[i] or "").strip()
        if not text or not kind:
            n_empty += 1
            continue
        if verified_only and verified_list is not None and i < len(verified_list):
            flag = verified_list[i]
            if flag is False or flag == 0 or flag == "False":
                n_unverified += 1
                continue
        keep.append(i)

    if len(keep) < n_folds * 2:
        md = (
            "Not enough labelled phrases for "
            f"{n_folds}-fold CV ({len(keep)} kept). {missing_hint}"
        )
        summary = {
            "n_input": len(raw_phrases),
            "n_kept": len(keep),
            "n_dropped_empty": n_empty,
            "n_dropped_unverified": n_unverified,
            "model": model,
        }
        return _jsonable(summary), [], [], [], md, len(keep)

    X = np.array([str(raw_phrases[i]).strip() for i in keep], dtype=object)
    y = np.array([raw_kinds[i] for i in keep], dtype=object)
    class_names = sorted(set(y.tolist()))
    counts = Counter(y.tolist())
    min_class = min(counts.values()) if counts else 0
    folds = min(n_folds, min_class)
    if folds < 2:
        md = (
            f"Smallest {label_name} has {min_class} phrases; need at least "
            "2 per class for stratified CV."
        )
        summary = {
            "n_input": len(raw_phrases),
            "n_kept": len(keep),
            "class_counts": dict(counts),
            "model": model,
        }
        return _jsonable(summary), [], [], [], md, len(keep)

    from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold

    rng = np.random.RandomState(seed)
    n = float(len(y))
    maj_acc = max(counts.values()) / n
    strat_dummy = sum((c / n) ** 2 for c in counts.values())

    vec = _vectorizer(
        model,
        ngram_min=ngram_min,
        ngram_max=ngram_max,
        min_df=min_df,
        max_features=max_features,
    )
    X_mat = vec.fit_transform(X)
    clf = _classifier(model, C=C, seed=seed)
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    splits = list(cv.split(X_mat, y))
    y_hat, acc_folds, bal_folds = _oof(clf, X_mat, y, splits)

    y_perm = y.copy()
    rng.shuffle(y_perm)
    perm_splits = list(
        StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed).split(
            X_mat, y_perm
        )
    )
    _perm_hat, perm_folds, _perm_bal = _oof(clf, X_mat, y_perm, perm_splits)
    perm_acc = float(perm_folds.mean())

    grouped_acc = None
    n_docs = 0
    if doc_ids is not None:
        docs = np.array([str(list(doc_ids)[i]) for i in keep], dtype=object)
        n_docs = int(len(set(docs.tolist())))
        if n_docs >= folds:
            try:
                gcv = StratifiedGroupKFold(
                    n_splits=folds, shuffle=True, random_state=seed
                )
                g_splits = list(gcv.split(X_mat, y, groups=docs))
                _g_hat, g_folds, _g_bal = _oof(clf, X_mat, y, g_splits)
                grouped_acc = float(g_folds.mean())
            except ValueError:
                grouped_acc = None

    from sklearn.metrics import classification_report, confusion_matrix

    report = classification_report(
        y, y_hat, labels=class_names, output_dict=True, zero_division=0
    )
    per_class = []
    for name in class_names:
        row = report.get(name) or {}
        per_class.append(
            {
                "kind": name,
                "precision": round(float(row.get("precision", 0.0)), 3),
                "recall": round(float(row.get("recall", 0.0)), 3),
                "f1": round(float(row.get("f1-score", 0.0)), 3),
                "support": int(row.get("support", counts[name])),
            }
        )

    cm = confusion_matrix(y, y_hat, labels=class_names)
    confusion = []
    for i, true in enumerate(class_names):
        for j, pred in enumerate(class_names):
            confusion.append(
                {"true": true, "pred": pred, "n": int(cm[i, j])}
            )

    error_by_format = []
    if groups is not None:
        by = defaultdict(lambda: [0, 0])
        grp_list = list(groups)
        for idx, i in enumerate(keep):
            g = str(grp_list[i]) if i < len(grp_list) else "unknown"
            by[g][1] += 1
            by[g][0] += int(y_hat[idx] != y[idx])
        for g, (err, tot) in sorted(by.items()):
            error_by_format.append(
                {
                    "format": g,
                    "n": tot,
                    "oof_error_rate": round(err / tot, 3) if tot else 0.0,
                }
            )

    error_ids = []
    if phrase_ids is not None:
        ids = list(phrase_ids)
        for idx, i in enumerate(keep):
            if y_hat[idx] != y[idx] and i < len(ids):
                error_ids.append(str(ids[i]))
                if len(error_ids) >= 40:
                    break

    full = _classifier(model, C=C, seed=seed)
    full.fit(X_mat, y)
    coefs = (
        _top_logreg_ngrams(full, vec, class_names) if model == "logreg" else []
    )

    acc_mean = float(acc_folds.mean())
    acc_std = float(acc_folds.std())
    bal_mean = float(bal_folds.mean())
    f1s = [row["f1"] for row in per_class]

    flags = []
    n_classes = max(1, len(class_names))
    chance = 1.0 / n_classes
    if acc_mean >= 0.95:
        flags.append(
            {
                "code": "lexical_collapse",
                "level": "warn",
                "message": (
                    f"Out-of-fold accuracy {acc_mean:.3f} is near-perfect. "
                    f"The {label_name} coding may have collapsed to keywords."
                ),
            }
        )
    if bal_mean < chance + 0.08:
        flags.append(
            {
                "code": "near_chance",
                "level": "warn",
                "message": (
                    f"Balanced accuracy {bal_mean:.3f} is within 0.08 of "
                    f"chance {chance:.3f} (1/{n_classes}). {label_name} "
                    "labels are not recoverable from this bag-of-words — "
                    "noisy coding, or a rule that is not in the text this "
                    "check can see."
                ),
            }
        )
    if acc_mean + 0.02 < maj_acc:
        flags.append(
            {
                "code": "below_majority",
                "level": "info",
                "message": (
                    f"Raw accuracy {acc_mean:.3f} is more than two points "
                    f"below the majority baseline {maj_acc:.3f}. That is "
                    "expected with class_weight=balanced on a dominant "
                    "class. Chance for this check is balanced accuracy "
                    f"versus {chance:.3f}, not accuracy versus majority."
                ),
            }
        )
    if grouped_acc is not None and grouped_acc + 0.10 < acc_mean:
        flags.append(
            {
                "code": "document_leakage",
                "level": "info",
                "message": (
                    f"Phrase-stratified accuracy {acc_mean:.3f} beats "
                    f"document-grouped accuracy {grouped_acc:.3f} by more "
                    "than 0.10. Some reconstructability is conversation "
                    f"style, not {label_name} lexicon."
                ),
            }
        )
    if f1s and min(f1s) < 0.35 and max(f1s) > 0.70:
        weak = [row["kind"] for row in per_class if row["f1"] < 0.35]
        flags.append(
            {
                "code": "class_collapse",
                "level": "warn",
                "message": (
                    f"{label_name} classes "
                    + ", ".join(weak)
                    + " have F1 < 0.35 while another class is recoverable. "
                    "The coder may be dumping leftovers into the weak class."
                ),
            }
        )
    if error_by_format and len(error_by_format) >= 2:
        rates = [row["oof_error_rate"] for row in error_by_format]
        if max(rates) - min(rates) >= 0.10:
            flags.append(
                {
                    "code": "format_gap",
                    "level": "info",
                    "message": (
                        "Out-of-fold error differs by ≥ 0.10 across formats. "
                        f"The {label_name} rule may not be applying evenly."
                    ),
                }
            )
    if not any(flag.get("level") == "warn" for flag in flags):
        flags.append(
            {
                "code": "consistent",
                "level": "ok",
                "message": (
                    f"Above chance: balanced accuracy {bal_mean:.3f} versus "
                    f"{chance:.3f} (1/{n_classes}). Majority {maj_acc:.3f} "
                    "is not the chance line — class-balanced models are "
                    f"allowed to sit near it. {label_name} labels look "
                    "lexically consistent."
                ),
            }
        )

    summary = {
        "n_input": len(raw_phrases),
        "n_kept": int(len(keep)),
        "n_dropped_empty": n_empty,
        "n_dropped_unverified": n_unverified,
        "n_docs": n_docs,
        "model": model,
        "label_name": label_name,
        "n_folds": int(folds),
        "ngram": [ngram_min, ngram_max],
        "class_counts": {k: int(v) for k, v in counts.items()},
        "accuracy_mean": round(acc_mean, 4),
        "accuracy_std": round(acc_std, 4),
        "accuracy_folds": [round(float(a), 4) for a in acc_folds],
        "balanced_accuracy_mean": round(bal_mean, 4),
        "majority_baseline": round(maj_acc, 4),
        "stratified_dummy": round(strat_dummy, 4),
        "permutation_accuracy": round(perm_acc, 4),
        "grouped_accuracy_mean": (
            None if grouped_acc is None else round(grouped_acc, 4)
        ),
        "per_class": per_class,
        "error_by_format": error_by_format,
        "n_oof_errors": int((y_hat != y).sum()),
        "oof_error_phrase_ids": error_ids,
        "chance": round(chance, 4),
    }
    if text_source:
        summary["text_source"] = text_source
    if label_mode:
        summary["label_mode"] = label_mode

    acc_rows = [
        {"measure": f"{folds}-fold accuracy", "value": acc_mean},
        {"measure": "accuracy std", "value": acc_std},
        {"measure": "balanced accuracy", "value": bal_mean},
        {"measure": "chance (1 / n classes)", "value": chance},
        {"measure": "majority baseline", "value": maj_acc},
        {"measure": "stratified dummy", "value": strat_dummy},
        {"measure": "shuffled-label accuracy", "value": perm_acc},
    ]
    if grouped_acc is not None:
        acc_rows.append(
            {"measure": "document-grouped accuracy", "value": grouped_acc}
        )

    cm_rows = []
    for true in class_names:
        row = {"true": true}
        for pred in class_names:
            n = next(
                c["n"]
                for c in confusion
                if c["true"] == true and c["pred"] == pred
            )
            row[pred] = n
        cm_rows.append(row)

    near_chance = any(f.get("code") == "near_chance" for f in flags)
    if near_chance:
        verdict = (
            f"**Verdict: near chance.** Balanced accuracy {bal_mean:.3f} "
            f"is within 0.08 of {chance:.3f}."
        )
    else:
        verdict = (
            f"**Verdict: above chance.** Balanced accuracy {bal_mean:.3f} "
            f"versus chance {chance:.3f} (1/{n_classes}). Raw accuracy "
            f"{acc_mean:.3f} next to majority {maj_acc:.3f} is not a "
            "chance test."
        )

    md_parts = [
        f"## {label_name} reconstruction (siding)",
        "",
        verdict,
        "",
        f"`{model}` bag-of-words, {folds}-fold stratified CV on "
        f"**{len(keep)}** phrases ({n_unverified} unverified dropped). "
        f"It asks whether a linear model can reconstruct **{label_name}** "
        f"from {TEXT_SOURCE_LABELS.get(text_source, 'the supplied text')}.",
        "",
        _md_table(acc_rows, [("Measure", "measure"), ("Value", "value")]),
        "",
        f"Read: the chance line is **balanced accuracy versus "
        f"{chance:.3f}**, not raw accuracy versus majority "
        f"({maj_acc:.3f}). Collapse is ≥ 0.95 raw accuracy. "
        "Document-grouped CV holds out whole conversations so we do not "
        "credit the same-chatbot wording twice.",
        "",
        f"### Per-{label_name} (out of fold)",
        "",
        _md_table(
            per_class,
            [
                (label_name, "kind"),
                ("Precision", "precision"),
                ("Recall", "recall"),
                ("F1", "f1"),
                ("n", "support"),
            ],
        ),
        "",
        f"### Confusion (rows = {label_name}, columns = BoW prediction)",
        "",
        _md_table(
            cm_rows,
            [("true", "true")] + [(name, name) for name in class_names],
            ndigits=0,
        ),
    ]
    if error_by_format:
        md_parts += [
            "",
            "### Out-of-fold error by format",
            "",
            _md_table(
                error_by_format,
                [
                    ("Format", "format"),
                    ("n", "n"),
                    ("error rate", "oof_error_rate"),
                ],
            ),
        ]
    if coefs:
        md_parts += [
            "",
            "### Heaviest n-grams (full-fit logistic regression, not CV)",
            "",
            _md_table(
                coefs,
                [(label_name, "kind"), ("n-gram", "ngram"), ("weight", "weight")],
            ),
        ]
    md_parts += ["", "### Flags", ""]
    for flag in flags:
        md_parts.append(f"- **{flag['code']}** ({flag['level']}): {flag['message']}")
    if error_ids:
        md_parts += [
            "",
            f"{len(error_ids)} example out-of-fold error `phrase_id`s "
            "(look them up in 02_embed; text is not stored here): "
            + ", ".join(f"`{i}`" for i in error_ids[:20]),
        ]
    md_parts += [
        "",
        "Other models on the same button: `nb` (multinomial naïve Bayes "
        "on counts; often strong on short phrases) and `linearsvc` "
        "(linear SVM on tf-idf). They answer the same question with a "
        "different linear family. Do not use the embedding space here — "
        "that would test grain geometry, not extract consistency.",
    ]
    md = "\n".join(md_parts)
    return (
        _jsonable(summary),
        _jsonable(confusion),
        _jsonable(coefs),
        _jsonable(flags),
        md,
        int(len(keep)),
    )


def hard_lens_labels(responsibilities, cluster_ids, topic_labels=None) -> list[str]:
    """Hard lens name per phrase: argmax of phrase-level ``QR``."""
    from .compare import _phrase_r, _topic_names

    R = _phrase_r(responsibilities, cluster_ids)
    names = _topic_names(topic_labels, R.shape[1])
    idx = np.asarray(R, float).argmax(axis=1)
    return [names[int(i)] for i in idx]
