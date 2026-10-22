"""CIP-0016: document histograms, cost, MDS, tests (no POT required)."""

import numpy as np
import pytest

from referia.assess.compute import Compute
from referia.assess.compute.distance import (
    _as_float_knob,
    _groups_for_docs,
    _jsonable,
    axis_correlates,
    chapter_display_name,
    classical_mds,
    cluster_ids_missing,
    cosine_ground_cost,
    distance_tests_markdown,
    document_soft_topic_distributions,
    emd_distance_matrix,
    load_document_titles,
    permanova,
    permdisp,
    run_document_distance_analysis,
    topic_means_from_responsibilities,
)


def test_soft_histograms_row_stochastic():
    doc_ids = ["A", "A", "B", "B"]
    R = np.array(
        [
            [1.0, 0.0],
            [0.5, 0.5],
            [0.0, 1.0],
            [0.0, 1.0],
        ]
    )
    P, kept, mass = document_soft_topic_distributions(doc_ids, R, min_mass=1.0)
    assert kept == ["A", "B"]
    assert P.shape == (2, 2)
    assert np.allclose(P.sum(axis=1), 1.0)
    assert mass[0] == 2.0
    assert mass[1] == 2.0
    assert np.allclose(P[0], [0.75, 0.25])


def test_min_mass_drops_small_docs():
    P, kept, _ = document_soft_topic_distributions(
        ["A", "B"],
        [[1.0, 0.0], [0.0, 1.0]],
        min_mass=2.0,
    )
    assert kept == []
    assert P.shape == (0, 2)


def test_topic_means_unit_rows():
    X = np.array([[3.0, 0.0], [0.0, 4.0]])
    R = np.array([[1.0, 0.0], [0.0, 1.0]])
    means = topic_means_from_responsibilities(X, R)
    assert means.shape == (2, 2)
    assert np.allclose(np.linalg.norm(means, axis=1), 1.0)


def test_cosine_ground_cost_zero_diagonal():
    means = np.array([[1.0, 0.0], [0.0, 1.0]])
    M = cosine_ground_cost(means)
    assert M.shape == (2, 2)
    assert np.allclose(np.diag(M), 0.0)
    assert np.all(M >= 0)
    assert M[0, 1] > 0.9


def test_classical_mds_hand_built_distance():
    D = np.array(
        [
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 0.0],
        ]
    )
    mds = classical_mds(D, n_components=2)
    assert mds["coords"].shape == (3, 2)
    assert len(mds["explained"]) == 2
    assert mds["negative_ratio"] >= 0.0


def test_permanova_permutation_count():
    D = np.array(
        [
            [0.0, 0.1, 1.0, 1.1],
            [0.1, 0.0, 1.1, 1.0],
            [1.0, 1.1, 0.0, 0.1],
            [1.1, 1.0, 0.1, 0.0],
        ]
    )
    res = permanova(D, ["g1", "g1", "g2", "g2"], n_perm=19, seed=0)
    assert res["n_perm"] == 19
    assert res["n_docs"] == 4
    assert res["n_groups"] == 2
    assert 0.0 <= res["p_value"] <= 1.0


def test_axis_correlates_jsonable():
    coords = np.array([[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]])
    P = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
    rows = axis_correlates(coords, P, topic_labels={"T0": "Privacy"}, top=1)
    assert rows
    assert all(set(r) >= {"axis", "end", "label", "r"} for r in rows)


def test_emd_missing_or_runs():
    P = np.array([[1.0, 0.0], [0.0, 1.0]])
    M = np.array([[0.0, 1.0], [1.0, 0.0]])
    try:
        D = emd_distance_matrix(P, M)
    except ImportError as exc:
        assert "referia[distance]" in str(exc)
        return
    assert D.shape == (2, 2)
    assert D[0, 1] == D[1, 0]
    assert D[0, 1] > 0


def test_facade_with_stub_emd(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: np.abs(P[:, None, :] - P[None, :, :]).sum(-1),
    )
    packed = run_document_distance_analysis(
        embeddings=[
            [1.0, 0.0],
            [0.9, 0.1],
            [0.8, 0.2],
            [0.7, 0.3],
            [0.2, 0.8],
            [0.1, 0.9],
            [0.0, 1.0],
            [0.15, 0.85],
        ],
        doc_ids=["A", "A", "B", "B", "C", "C", "D", "D"],
        responsibilities=[
            [1.0, 0.0],
            [1.0, 0.0],
            [0.9, 0.1],
            [0.8, 0.2],
            [0.2, 0.8],
            [0.1, 0.9],
            [0.0, 1.0],
            [0.0, 1.0],
        ],
        groups=["g1", "g1", "g1", "g1", "g2", "g2", "g2", "g2"],
        topic_labels={"T0": "Privacy", "T1": "Access"},
        min_mass=1.0,
        n_perm=9,
        seed=0,
    )
    assert len(packed) == 17
    P, means, mass, docs, cost, D, coords, explained, perm, disp, axes, md, mds_spec, heat, emd, bars, radar = packed
    assert docs == ["A", "B", "C", "D"]
    assert np.allclose(np.sum(P, axis=1), 1.0)
    assert "PERMANOVA" in md
    assert mds_spec["data"][0]["customdata"][0]["doc"] in docs
    assert heat["data"][0]["type"] == "heatmap"
    assert radar["data"][0]["type"] == "scatterpolar"


def test_distance_functions_registered():
    names = {e["name"] for e in Compute({"input": {}})._compute_functions_list()}
    assert "run_document_distance_analysis" in names
    assert "document_soft_topic_distributions" in names
    assert "emd_distance_matrix" in names


def test_shape_errors():
    with pytest.raises(ValueError, match="2-D"):
        document_soft_topic_distributions(["A"], [1.0, 0.0])
    with pytest.raises(ValueError, match="doc_ids"):
        document_soft_topic_distributions(["A"], [[1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError, match="embeddings rows"):
        topic_means_from_responsibilities([[1.0, 0.0]], [[1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError, match="document axis"):
        axis_correlates([[0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]])


def test_jsonable_and_empty_mds():
    assert _jsonable({"a": np.int64(3), "b": (np.array([1.0]),)}) == {"a": 3, "b": [[1.0]]}
    marker = object()
    assert _jsonable(marker) is marker
    empty = classical_mds(np.zeros((0, 0)), n_components=2)
    assert empty["coords"].shape == (0, 2)
    assert empty["negative_ratio"] == 0.0
    zeros = classical_mds(np.zeros((3, 3)), n_components=2)
    assert zeros["coords"].shape == (3, 2)
    assert np.allclose(zeros["coords"], 0.0)


def test_permanova_and_permdisp_degenerate():
    D = np.zeros((2, 2))
    single = permanova(D, ["g", "g"], n_perm=0)
    assert single["p_value"] == 1.0
    disp = permdisp(D, ["a", "a", "b", "b"][:2], n_perm=0)
    assert disp["p_value"] == 1.0
    four = np.zeros((4, 4))
    disp4 = permdisp(four, ["a", "a", "b", "b"], n_perm=0)
    assert disp4["p_value"] == 1.0
    assert set(disp4["mean_distance_to_centroid"]) == {"a", "b"}


def test_axis_correlates_zero_variance():
    coords = np.zeros((2, 2))
    P = np.array([[1.0, 0.0], [1.0, 0.0]])
    rows = axis_correlates(coords, P, topic_labels={0: "Privacy"}, top=1)
    assert rows
    assert all(r["r"] == 0.0 for r in rows)


def test_distance_tests_markdown_sections():
    md = distance_tests_markdown(
        {
            "pseudo_F": 1.2,
            "R2": 0.4,
            "p_value": 0.05,
            "n_perm": 9,
            "n_docs": 4,
            "n_groups": 2,
        },
        {"F": 0.8, "p_value": 0.2, "mean_distance_to_centroid": {"g1": 0.1}},
        [{"axis": 1, "end": "positive", "label": "Privacy", "r": 0.9}],
        note="install hint",
    )
    assert "install hint" in md
    assert "PERMANOVA" in md
    assert "g1" in md
    assert "Privacy" in md


def test_emd_with_stub_ot_module(monkeypatch):
    import sys
    import types

    fake = types.ModuleType("ot")
    fake.emd2 = lambda a, b, M: 0.25
    monkeypatch.setitem(sys.modules, "ot", fake)
    D = emd_distance_matrix([[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]])
    assert D.shape == (2, 2)
    assert D[0, 1] == 0.25


def test_facade_notes_missing_groups_and_pot(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda *a, **k: (_ for _ in ()).throw(
            ImportError("pip install 'referia[distance]'")
        ),
    )
    packed = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["A", "B"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        min_mass=1.0,
        group_field="group",
    )
    assert "No group labels" in packed[11]
    assert "referia[distance]" in packed[11]


def test_facade_doc_group_and_phrase_groups(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: np.abs(P[:, None, :] - P[None, :, :]).sum(-1),
    )
    via_map = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0], [0.2, 0.8], [0.1, 0.9]],
        doc_ids=["A", "B", "C", "D"],
        responsibilities=[[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]],
        doc_group={"A": "g1", "B": "g1", "C": "g2", "D": "g2"},
        min_mass=1.0,
        n_perm=5,
        seed=0,
    )
    assert via_map[3] == ["A", "B", "C", "D"]
    assert via_map[8]["n_groups"] == 2

    via_phrases = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
        doc_ids=["A", "A", "B", "B"],
        responsibilities=[[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]],
        groups=["g1", "g1", "g2", "g2"],
        min_mass=1.0,
        n_perm=5,
        seed=0,
    )
    assert via_phrases[3] == ["A", "B"]
    assert via_phrases[8]["n_docs"] == 2

    via_docs = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["A", "B"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        groups=["g1", "g2"],
        min_mass=1.0,
        n_perm=5,
        seed=0,
    )
    assert via_docs[8]["n_groups"] == 2

    mismatched = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["A", "B"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        groups=["only-one"],
        min_mass=1.0,
    )
    assert "No group labels" in mismatched[11]


def test_run_document_distance_expands_vq_qr(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: np.abs(P[:, None, :] - P[None, :, :]).sum(-1),
    )
    packed = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
        doc_ids=["A", "A", "B", "B"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        cluster_ids=[0, 0, 1, 1],
        groups=["g1", "g1", "g2", "g2"],
        min_mass=1.0,
        n_perm=5,
        seed=0,
    )
    P, _means, mass, docs, *_rest = packed
    assert docs == ["A", "B"]
    np.testing.assert_allclose(P, [[1.0, 0.0], [0.0, 1.0]])
    np.testing.assert_allclose(mass, [2.0, 2.0])
    with pytest.raises(ValueError, match="pass cluster_ids"):
        run_document_distance_analysis(
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
            doc_ids=["A", "B"],
            responsibilities=[[1.0, 0.0]],
            min_mass=1.0,
        )
    with pytest.raises(ValueError, match="expanded responsibilities"):
        run_document_distance_analysis(
            embeddings=[[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
            doc_ids=["A", "B", "C"],
            responsibilities=[[1.0, 0.0], [0.0, 1.0]],
            cluster_ids=[0, 1],
            min_mass=1.0,
        )


def test_zero_mass_kept_when_min_mass_none():
    P, kept, mass = document_soft_topic_distributions(
        ["A"],
        [[0.0, 0.0]],
        min_mass=None,
    )
    assert kept == ["A"]
    assert P.shape == (1, 2)
    assert mass == [0.0]


def test_cluster_ids_missing_accepts_numpy_array():
    assert cluster_ids_missing(None) is True
    assert cluster_ids_missing("") is True
    assert cluster_ids_missing("   ") is True
    assert cluster_ids_missing(float("nan")) is True
    assert cluster_ids_missing(np.array([0, 0, 1, 1])) is False
    assert cluster_ids_missing(np.array([], dtype=int)) is True
    assert cluster_ids_missing("[0, 1, 1]") is False
    assert cluster_ids_missing("not-json") is True
    assert cluster_ids_missing(np.array([None], dtype=object)) is True
    assert cluster_ids_missing(np.array([[0, 1]], dtype=object)) is False

    class _NoArray:
        def __array__(self, dtype=None):
            raise ValueError("cannot convert")

    assert cluster_ids_missing(_NoArray()) is True


def test_cluster_ids_missing_isfinite_typeerror(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist.np,
        "isfinite",
        lambda value: (_ for _ in ()).throw(TypeError("no")),
    )
    assert cluster_ids_missing(1.0) is False


def test_chapter_display_name_and_nan_min_mass(monkeypatch):
    from referia.assess.compute.distance import chapter_display_name

    assert chapter_display_name("foreword.pdf") == "Foreword"
    assert chapter_display_name("chapter_2.pdf") == "Chapter 2"
    assert chapter_display_name(
        "chapter_2.pdf", {"chapter_2.pdf": "2. Closing the innovation gap"}
    ) == "2. Closing the innovation gap"

    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: np.abs(P[:, None, :] - P[None, :, :]).sum(-1),
    )
    packed = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["chapter_1.pdf", "chapter_2.pdf"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        min_mass=float("nan"),
        group_field="chapter",
        n_perm=5,
        seed=0,
    )
    assert packed[3] == ["chapter_1.pdf", "chapter_2.pdf"]
    assert packed[13]["data"][0]["y"] == ["Chapter 1", "Chapter 2"]
    assert "PERMANOVA is not identified" in packed[11]
    assert packed[16]["data"][0]["type"] == "scatterpolar"


def test_compute_wrapper_loads_codebook_cluster_ids(tmp_path, monkeypatch):
    import pandas as pd
    from referia.assess.compute import distance as dist

    info = tmp_path / "info"
    info.mkdir()
    pd.DataFrame({"cluster_ids": [[0, 0, 1, 1]]}).to_parquet(info / "codebook.parquet")
    (info / "documents.yml").write_text(
        "- filename: chapter_1.pdf\n  title: '1. Starting point'\n"
        "- filename: chapter_2.pdf\n  title: '2. Innovation'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: np.abs(P[:, None, :] - P[None, :, :]).sum(-1),
    )
    compute = Compute(
        {
            "input": {
                "type": "parquet",
                "filename": "records.parquet",
                "directory": str(info),
            }
        }
    )
    packed = compute._run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
        doc_ids=["chapter_1.pdf", "chapter_1.pdf", "chapter_2.pdf", "chapter_2.pdf"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        min_mass=1.0,
        group_field="chapter",
        n_perm=5,
        seed=0,
    )
    assert packed[3] == ["chapter_1.pdf", "chapter_2.pdf"]
    assert packed[16]["data"][0]["name"] == "1. Starting point"
    np.testing.assert_allclose(packed[0], [[1.0, 0.0], [0.0, 1.0]])


def test_chapter_display_name_stem_and_fallback():
    assert chapter_display_name(
        "files/foreword.pdf", {"foreword.pdf": "Opening"}
    ) == "Opening"
    assert chapter_display_name(
        "files/foreword.pdf", {"foreword": "Opening stem"}
    ) == "Opening stem"
    assert chapter_display_name("closing_the_gap.pdf") == "closing the gap"


def test_load_document_titles_skips_bad_rows(tmp_path, monkeypatch):
    missing = load_document_titles(tmp_path / "absent.yml")
    assert missing == {}
    path = tmp_path / "documents.yml"
    path.write_text(
        "- just a string\n"
        "- filename: a.pdf\n"
        "- filename: b.pdf\n  title: 'B title'\n",
        encoding="utf-8",
    )
    assert load_document_titles(path) == {"b.pdf": "B title"}

    import builtins

    real_import = builtins.__import__

    def _block_yaml(name, *args, **kwargs):
        if name == "yaml" or name.startswith("yaml."):
            raise ImportError("yaml blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_yaml)
    assert load_document_titles(path) == {}


def test_as_float_knob_and_groups_for_docs():
    assert _as_float_knob(None, 1.0) == 1.0
    assert _as_float_knob("", 2.5) == 2.5
    assert _as_float_knob("bad", 3.0) == 3.0
    assert _as_float_knob([], 4.0) == 4.0
    docs = ["a.pdf", "b.pdf"]
    assert _groups_for_docs(docs, group_field="chapter") == ["a", "b"]
    assert _groups_for_docs(
        docs, group_field="doc", display_names=["One", "Two"]
    ) == ["One", "Two"]
    assert _groups_for_docs(
        docs, doc_group={"a.pdf": "survey", "b.pdf": "dialogue"}
    ) == ["survey", "dialogue"]
    assert _groups_for_docs(docs, groups=None) is None
    assert _groups_for_docs(docs, groups=["s", "d"]) == ["s", "d"]
    assert _groups_for_docs(
        docs,
        groups=["s", "s", "d", "d"],
        doc_ids=["a.pdf", "a.pdf", "b.pdf", "b.pdf"],
    ) == ["s", "d"]
    assert _groups_for_docs(docs, groups=["only-one"]) is None


def _patch_emd(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: np.abs(P[:, None, :] - P[None, :, :]).sum(-1),
    )


def test_run_distance_expands_json_cluster_ids(monkeypatch):
    _patch_emd(monkeypatch)
    packed = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
        doc_ids=["a.pdf", "a.pdf", "b.pdf", "b.pdf"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        cluster_ids="[0, 0, 1, 1]",
        min_mass="",
        group_field="chapter",
        n_perm=5,
        seed=0,
    )
    assert packed[3] == ["a.pdf", "b.pdf"]
    np.testing.assert_allclose(packed[0], [[1.0, 0.0], [0.0, 1.0]])


def test_run_distance_requires_cluster_ids_when_shapes_differ():
    with pytest.raises(ValueError, match="pass cluster_ids"):
        run_document_distance_analysis(
            embeddings=[[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
            doc_ids=["a.pdf", "a.pdf", "b.pdf"],
            responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        )


def test_run_distance_expanded_shape_mismatch():
    with pytest.raises(ValueError, match="expanded responsibilities"):
        run_document_distance_analysis(
            embeddings=[[1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.2, 0.8]],
            doc_ids=["a.pdf"] * 4,
            responsibilities=[[1.0, 0.0], [0.0, 1.0]],
            cluster_ids=[0, 0],
        )


def test_run_distance_emd_import_error_and_no_groups(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: (_ for _ in ()).throw(ImportError("POT is required")),
    )
    packed = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["a.pdf", "b.pdf"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        min_mass=1.0,
        n_perm=5,
        seed=0,
    )
    assert "POT is required" in packed[11]
    assert packed[5] == [[0.0, 0.0], [0.0, 0.0]]
    assert "No group labels" in packed[11]


def test_run_distance_doc_group_and_empty_min_mass(monkeypatch):
    _patch_emd(monkeypatch)
    packed = run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["a.pdf", "b.pdf"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        doc_group={"a.pdf": "survey", "b.pdf": "dialogue"},
        min_mass="not-a-number",
        n_perm=5,
        seed=0,
        topic_labels={"T0": "Privacy", "T1": "Access"},
    )
    assert "PERMANOVA" in packed[11]
    assert packed[16]["data"][0]["type"] == "scatterpolar"


class _Iface:
    def __init__(self, directory=None, stores=None):
        self.directory = directory
        self._stores = stores or {}

    def get(self, key, default=None):
        return self._stores.get(key, default)


def test_config_info_dir_fallbacks(tmp_path):
    compute = Compute({"input": {}})
    compute._interface = None
    assert compute._config_info_dir() is None

    compute._interface = _Iface(directory=None, stores={})
    assert compute._config_info_dir() is None

    base = tmp_path / "04_distance"
    compute._interface = _Iface(directory=str(base), stores={})
    assert compute._config_info_dir() == base / ".." / "info"

    info = tmp_path / "info"
    compute._interface = _Iface(
        directory=None,
        stores={"data": {"directory": str(info), "filename": "records.parquet"}},
    )
    assert compute._config_info_dir() == info

    compute._interface = _Iface(
        directory=str(base),
        stores={"input": {"directory": "../info", "filename": "records.parquet"}},
    )
    assert compute._config_info_dir() == base / "../info"


def test_compute_wrapper_codebook_errors_and_titles(tmp_path, monkeypatch):
    _patch_emd(monkeypatch)
    info = tmp_path / "info"
    info.mkdir()
    (info / "codebook.parquet").write_bytes(b"not a parquet")
    (info / "documents.yml").write_text(
        "- filename: a.pdf\n  title: 'From yaml'\n"
        "- filename: b.pdf\n  title: 'Also yaml'\n",
        encoding="utf-8",
    )
    compute = Compute(
        {
            "input": {
                "type": "parquet",
                "filename": "records.parquet",
                "directory": str(info),
            }
        }
    )
    with pytest.raises(ValueError, match="pass cluster_ids"):
        compute._run_document_distance_analysis(
            embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
            doc_ids=["a.pdf", "a.pdf", "b.pdf", "b.pdf"],
            responsibilities=[[1.0, 0.0], [0.0, 1.0]],
            min_mass=1.0,
        )

    import pandas as pd

    pd.DataFrame({"n_vq": [2]}).to_parquet(info / "codebook.parquet")
    with pytest.raises(ValueError, match="pass cluster_ids"):
        compute._run_document_distance_analysis(
            embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
            doc_ids=["a.pdf", "a.pdf", "b.pdf", "b.pdf"],
            responsibilities=[[1.0, 0.0], [0.0, 1.0]],
            min_mass=1.0,
        )

    pd.DataFrame({"cluster_ids": []}).to_parquet(info / "codebook.parquet")
    packed = compute._run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["a.pdf", "b.pdf"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        min_mass=1.0,
        group_field="chapter",
        n_perm=5,
        seed=0,
    )
    assert packed[16]["data"][0]["name"] == "From yaml"

    packed = compute._run_document_distance_analysis(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        doc_ids=["a.pdf", "b.pdf"],
        responsibilities=[[1.0, 0.0], [0.0, 1.0]],
        cluster_ids=[0, 1],
        doc_titles={"a.pdf": "Given A", "b.pdf": "Given B"},
        min_mass=1.0,
        group_field="chapter",
        n_perm=5,
        seed=0,
    )
    assert packed[16]["data"][0]["name"] == "Given A"
