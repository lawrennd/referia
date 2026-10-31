"""Compute wrappers that load study stores for sequence / multiverse."""

from pathlib import Path
from unittest.mock import patch

from referia.assess.compute import Compute


class _Iface:
    def __init__(self, directory: str, info_dir: str = "info"):
        self.directory = directory
        self._info_dir = info_dir

    def get(self, key, default=None):
        if key == "input":
            return {"directory": self._info_dir, "filename": "constants.yml"}
        return default


def _compute(tmp_path: Path) -> tuple[Compute, Path]:
    info = tmp_path / "info"
    info.mkdir()
    compute = Compute({"input": {}})
    compute._interface = _Iface(str(tmp_path))
    return compute, info


def test_study_files_dir_and_resolve_files_root(tmp_path: Path):
    compute, _info = _compute(tmp_path)
    assert compute._study_files_dir() == (tmp_path / "files").resolve()
    abs_root = tmp_path / "elsewhere"
    abs_root.mkdir()
    assert compute._resolve_files_root(str(abs_root)) == abs_root
    assert compute._resolve_files_root("files") == (tmp_path / "files").resolve()
    compute._interface.directory = None
    assert compute._resolve_files_root("files").name == "files"
    assert Compute({"input": {}})._study_files_dir() is None


def test_coded_phrase_rows_joins_grounds(tmp_path: Path):
    compute, info = _compute(tmp_path)
    (info / "phrases.yml").write_text(
        "- phrase_id: p1\n  phrase: rules\n- phrase_id: p2\n  phrase: skip\n",
        encoding="utf-8",
    )
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: personal_experience\n",
        encoding="utf-8",
    )
    rows = compute._coded_phrase_rows()
    assert len(rows) == 1
    assert rows[0]["basis"] == "personal_experience"
    assert Compute({"input": {}})._coded_phrase_rows() == []


def test_docx_paragraphs_import_and_read_errors(tmp_path: Path):
    compute, _info = _compute(tmp_path)
    dummy = tmp_path / "x.docx"
    dummy.write_bytes(b"not a docx")
    assert compute._docx_paragraphs(dummy) is None

    real_import = __import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "docx" or (fromlist and name == "docx"):
            raise ImportError("docx missing")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=_import):
        assert compute._docx_paragraphs(dummy) is None

    class _Doc:
        def __init__(self, *_a, **_k):
            self.paragraphs = [type("P", (), {"text": "hello"})()]

    fake_docx = type("mod", (), {"Document": _Doc})
    with patch.dict("sys.modules", {"docx": fake_docx}):
        assert compute._docx_paragraphs(dummy) == ["hello"]


def test_rebuild_speaker_turns_from_files_root(tmp_path: Path):
    compute, info = _compute(tmp_path)
    (info / "documents.yml").write_text(
        "- filename: workshops/a.docx\n  format: workshop\n  round: spring_2026\n"
        "- filename: workshops/gone.docx\n  format: workshop\n  round: spring_2026\n"
        "- filename: chatbot/x.docx\n  format: chatbot\n  round: spring_2026\n",
        encoding="utf-8",
    )
    workshops = tmp_path / "files" / "workshops"
    workshops.mkdir(parents=True)
    (workshops / "a.docx").write_bytes(b"fake")

    def _paras(path):
        if Path(path).name == "a.docx":
            return ["Speaker 1: welcome", "Speaker 2: I saw this last year"]
        raise OSError("unreadable")

    compute._docx_paragraphs = _paras
    turns, md, n = compute._run_rebuild_speaker_turns(
        facilitator_names="Alex, Sam",
        files_root="files",
    )
    assert n == 2
    assert "I saw this" not in md
    assert turns[0]["facilitator"] is True

    preloaded, _md, n2 = compute._run_rebuild_speaker_turns(
        documents=[
            {
                "filename": "workshops/a.docx",
                "format": "workshop",
                "round": "spring_2026",
            }
        ],
        paragraphs_by_filename={
            "workshops/a.docx": ["Speaker 2: hello there"]
        },
    )
    assert n2 == 1
    assert preloaded[0]["speaker"] == "s2"


def test_stories_follow_stories_loads_turns_and_grounds(tmp_path: Path):
    compute, info = _compute(tmp_path)
    (info / "turns.yml").write_text(
        "- doc_id: workshops/a.docx\n  turn_i: 0\n  speaker: s2\n"
        "  facilitator: false\n  text: I saw this last year\n"
        "  round: spring_2026\n",
        encoding="utf-8",
    )
    (info / "grounds.yml").write_text(
        "- doc_id: workshops/a.docx\n  quote: I saw this last year\n"
        "  basis: personal_experience\n  format: workshop\n"
        "  round: spring_2026\n  unit_id: workshops/a.docx::c0003\n",
        encoding="utf-8",
    )
    rows, md, n = compute._run_stories_follow_stories(
        n_shuffles=8, seed=0, lookbacks=[1]
    )
    assert n == 1
    assert rows == [] or "lookback" in rows[0]
    assert "I saw this" not in md


def test_analysis_multiverse_loads_coded_phrases(tmp_path: Path):
    compute, info = _compute(tmp_path)
    (info / "phrases.yml").write_text(
        "- phrase_id: p1\n  format: workshop\n  doc_id: workshops/a.docx\n"
        "  round: spring_2026\n  session_type: breakout\n"
        "  quote_support: 1.0\n  unit_id: workshops/a.docx::c0003\n"
        "  extract_text: 'Speaker 2: a line'\n  lens: T0\n"
        "- phrase_id: p2\n  format: chatbot\n  doc_id: autumn_2025::1\n"
        "  round: autumn_2025\n  session_type: chatbot\n"
        "  quote_support: 1.0\n  unit_id: autumn_2025::1::c0003\n"
        "  extract_text: principle\n  lens: T1\n",
        encoding="utf-8",
    )
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: personal_experience\n"
        "- phrase_id: p2\n  basis: principle\n",
        encoding="utf-8",
    )
    summary, md, n_cfg = compute._run_analysis_multiverse(n_jsd_shuffles=0)
    assert n_cfg > 0
    assert summary
    assert "1080 populate-all" in md

    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    empty_compute, _ = _compute(empty_root)
    _summary, hint, z = empty_compute._run_analysis_multiverse()
    assert z == 0
    assert "07_grounds" in hint


def test_load_info_yaml_missing_file_and_stat_error(tmp_path: Path):
    compute, info = _compute(tmp_path)
    assert compute._load_info_yaml_rows("nope.yml") == []
    path = info / "turns.yml"
    path.write_text("- turn_id: a\n", encoding="utf-8")
    first = compute._load_info_yaml_rows("turns.yml")
    assert first[0]["turn_id"] == "a"
    assert compute._load_info_yaml_rows("turns.yml") is first
    real_exists = Path.exists
    real_stat = Path.stat

    def _exists(self):
        if self.name == "turns.yml":
            return True
        return real_exists(self)

    def _stat(self, *args, **kwargs):
        if self.name == "turns.yml":
            raise OSError("gone")
        return real_stat(self, *args, **kwargs)

    compute._info_yaml_cache = {}
    with patch.object(Path, "exists", _exists), patch.object(Path, "stat", _stat):
        assert compute._load_info_yaml_rows("turns.yml") == []


def test_registry_includes_sequence_and_multiverse():
    names = {e["name"] for e in Compute({"input": {}})._compute_functions_list()}
    assert "run_rebuild_speaker_turns" in names
    assert "run_stories_follow_stories" in names
    assert "run_analysis_multiverse" in names
